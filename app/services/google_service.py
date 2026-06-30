"""
Google Slides service module.

Provides a reusable service for interacting with the Google Slides and Google Drive APIs.
Handles presentation creation, content population, sharing, and deletion using
OAuth Installed App credentials.
"""
import json
import logging
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models.slide import SlideData

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive",
]

# Map layout hints to valid Google Slides predefined layout names.
LAYOUT_MAP = {
    "TITLE": "TITLE",
    "BULLETS": "TITLE_AND_BODY",
    "TWO_COLUMN": "TITLE_AND_BODY",
    "CLOSING": "TITLE_AND_BODY",
}
DEFAULT_LAYOUT = "TITLE_AND_BODY"


TOKEN_PATH = "credentials/token.json"
CLIENT_SECRET_PATH = "credentials/client_secret.json"


class GoogleSlidesService:
    """
    Service for creating, populating, sharing, and deleting Google Slides presentations.

    Authenticates using an OAuth Installed App flow. On first run it opens a
    browser for the user to log in. The resulting token is cached at
    credentials/token.json and refreshed automatically on subsequent runs.
    """

    def __init__(self) -> None:
        """
        Initialize the GoogleSlidesService.

        Loads credentials from credentials/token.json if they exist and are
        still valid. Refreshes expired credentials automatically. If no valid
        token is found, launches the browser-based OAuth consent flow and saves
        the new token to credentials/token.json.

        Raises:
            FileNotFoundError: If credentials/client_secret.json is missing.
            Exception: If authentication or API client initialization fails.
        """
        creds: Credentials | None = None

        # Load existing token if available.
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            logger.info("Loaded cached OAuth token from %s.", TOKEN_PATH)

        # Refresh or re-authenticate as needed.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("OAuth token expired. Refreshing...")
                creds.refresh(Request())
            else:
                logger.info("No valid token found. Launching OAuth consent flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save refreshed or newly acquired token.
            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info("OAuth token saved to %s.", TOKEN_PATH)

        self._slides = build("slides", "v1", credentials=creds)
        self._drive = build("drive", "v3", credentials=creds)

        logger.info("GoogleSlidesService authenticated successfully.")

    def create_presentation(self, title: str) -> str:
        """
        Create a new blank Google Slides presentation.

        Args:
            title: The title of the new presentation.

        Returns:
            The presentation ID of the newly created presentation.

        Raises:
            HttpError: If the Google Slides API call fails.
        """
        try:
            presentation = (
                self._slides.presentations()
                .create(body={"title": title})
                .execute()
            )
        except HttpError as exc:
            print("STATUS:", exc.status_code)
            print("CONTENT:", exc.content.decode("utf-8", errors="ignore"))
            logger.error("Failed to create presentation '%s': %s", title, exc)
            raise

        presentation_id = presentation["presentationId"]
        logger.info("Presentation created. ID: %s", presentation_id)
        return presentation_id

    def populate_presentation(
        self,
        presentation_id: str,
        slides: list[SlideData],
    ) -> None:
        """
        Populate a presentation with content from a list of SlideData objects.

        For each SlideData:
          1. Creates a new slide (no placeholderIdMappings).
          2. Fetches the created slide via presentations().get().
          3. Dynamically discovers the real TITLE and BODY placeholder object IDs
             from the slide's pageElements.
          4. Inserts title and body text via a batchUpdate.

        The default blank slide is deleted after all content slides are created.

        Args:
            presentation_id: The ID of the target presentation.
            slides: The list of SlideData objects to insert into the presentation.

        Raises:
            HttpError: If any Google Slides API call fails.
        """
        try:
            # Get the IDs of any default slides so we can delete them later.
            initial = (
                self._slides.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )
            default_slide_ids = [s["objectId"] for s in initial.get("slides", [])]

            for slide_data in slides:
                slide_object_id = f"slide_{slide_data.slide_index}"
                layout_name = LAYOUT_MAP.get(slide_data.layout_hint, DEFAULT_LAYOUT)

                # Step 1: Create the slide without any placeholderIdMappings.
                self._slides.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": [{
                        "createSlide": {
                            "objectId": slide_object_id,
                            "slideLayoutReference": {
                                "predefinedLayout": layout_name,
                            },
                        }
                    }]},
                ).execute()

                # Step 2: Fetch the slide to discover the real placeholder IDs.
                presentation_data = (
                    self._slides.presentations()
                    .get(presentationId=presentation_id)
                    .execute()
                )

                # Find the newly created slide by its objectId.
                target_slide = next(
                    (s for s in presentation_data.get("slides", [])
                     if s["objectId"] == slide_object_id),
                    None,
                )

                if not target_slide:
                    logger.warning(
                        "Could not locate slide '%s' after creation. Skipping.",
                        slide_object_id,
                    )
                    continue

                # Step 3: Discover TITLE and BODY placeholder IDs from pageElements.
                title_id: str | None = None
                body_id: str | None = None

                for element in target_slide.get("pageElements", []):
                    shape = element.get("shape", {})
                    placeholder = shape.get("placeholder", {})
                    p_type = placeholder.get("type", "")
                    if p_type == "TITLE" and title_id is None:
                        title_id = element["objectId"]
                    elif p_type in ("BODY", "SUBTITLE") and body_id is None:
                        body_id = element["objectId"]

                # Step 4: Insert title and body text using the discovered IDs.
                text_requests = []

                if title_id and slide_data.title:
                    text_requests.append({
                        "insertText": {
                            "objectId": title_id,
                            "text": slide_data.title,
                        }
                    })

                if body_id and slide_data.body_text:
                    body_text = "\n".join(slide_data.body_text)
                    text_requests.append({
                        "insertText": {
                            "objectId": body_id,
                            "text": body_text,
                        }
                    })

                if text_requests:
                    self._slides.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={"requests": text_requests},
                    ).execute()

                logger.info(
                    "Slide %d/%d populated: title_id=%s body_id=%s",
                    slide_data.slide_index,
                    len(slides),
                    title_id,
                    body_id,
                )

            # Step 5: Delete the original default blank slides.
            if default_slide_ids:
                delete_requests = [
                    {"deleteObject": {"objectId": sid}} for sid in default_slide_ids
                ]
                self._slides.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={"requests": delete_requests},
                ).execute()
                logger.info("Deleted %d default slide(s).", len(default_slide_ids))

        except HttpError as exc:
            logger.error(
                "Failed to populate presentation '%s': %s", presentation_id, exc
            )
            raise

        logger.info(
            "Populated presentation '%s' with %d slides.",
            presentation_id,
            len(slides),
        )

    def share_presentation(self, presentation_id: str) -> str:
        """
        Share the presentation publicly with anyone who has the link as a viewer.

        Args:
            presentation_id: The ID of the presentation to share.

        Returns:
            The public view URL of the shared presentation.

        Raises:
            HttpError: If the Google Drive API call fails.
        """
        try:
            self._drive.permissions().create(
                fileId=presentation_id,
                body={
                    "type": "anyone",
                    "role": "reader",
                },
            ).execute()
        except HttpError as exc:
            logger.error(
                "Failed to share presentation '%s': %s", presentation_id, exc
            )
            raise

        url = f"https://docs.google.com/presentation/d/{presentation_id}/edit?usp=sharing"
        logger.info("Presentation '%s' shared publicly. URL: %s", presentation_id, url)
        return url

    def delete_presentation(self, presentation_id: str) -> None:
        """
        Permanently delete a presentation from Google Drive.

        Used when the review agent fails the presentation quality check.

        Args:
            presentation_id: The ID of the presentation to delete.

        Raises:
            HttpError: If the Google Drive API call fails.
        """
        try:
            self._drive.files().delete(fileId=presentation_id).execute()
        except HttpError as exc:
            logger.error(
                "Failed to delete presentation '%s': %s", presentation_id, exc
            )
            raise

        logger.info("Presentation '%s' deleted successfully.", presentation_id)
