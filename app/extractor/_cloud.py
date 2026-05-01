import json
from io import BytesIO
from typing import Any, Dict, Optional, Union

import cloudinary
import cloudinary.api
import cloudinary.uploader
from curl_cffi import requests


class CloudinaryDataManager:
    """
    A class to manage text/JSON data storage in Cloudinary using raw resource type.
    Handles both upload and retrieval operations without saving to local files.
    """

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        """
        Initialize Cloudinary configuration.

        Args:
            cloud_name: Your Cloudinary cloud name
            api_key: Your Cloudinary API key
            api_secret: Your Cloudinary API secret
        """
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )

    def upload_text(self,
                    text_content: str,
                    public_id: str,
                    folder: str = "api_requests",
                    access_mode: str = "public",
                    overwrite: bool = True) -> Dict[str, Any]:
        """
        Upload plain text data to Cloudinary.

        Args:
            text_content: The text content to upload
            public_id: Unique identifier for the file (include .txt extension)
            folder: Folder path in Cloudinary
            access_mode: 'public' or 'authenticated'
            overwrite: Whether to overwrite existing file

        Returns:
            Upload result dictionary from Cloudinary
        """
        buffer = BytesIO()
        buffer.write(text_content.encode('utf-8'))
        buffer.seek(0)

        result = cloudinary.uploader.upload(
            buffer,
            public_id=public_id,
            resource_type="raw",
            folder=folder,
            access_mode=access_mode,
            overwrite=overwrite
        )

        return result

    def upload_json(self,
                    json_data: Union[Dict, list],
                    public_id: str,
                    folder: str = "api_requests",
                    access_mode: str = "public",
                    indent: Optional[int] = None,
                    overwrite: bool = True
                    ) -> Dict[str, Any]:
        """
        Upload JSON data to Cloudinary.

        Args:
            json_data: Python dictionary or list to upload as JSON
            public_id: Unique identifier for the file (include .json extension)
            folder: Folder path in Cloudinary
            access_mode: 'public' or 'authenticated'
            indent: JSON indentation for readability
            overwrite: Whether to overwrite existing file

        Returns:
            Upload result dictionary from Cloudinary
        """
        json_string = json.dumps(json_data, indent=indent)

        buffer = BytesIO()
        buffer.write(json_string.encode('utf-8'))
        buffer.seek(0)

        result = cloudinary.uploader.upload(
            buffer,
            public_id=public_id,
            resource_type="raw",
            folder=folder,
            access_mode=access_mode,
            overwrite=overwrite
        )

        return result

    def upload_from_request_data(self,
                                 request_data: Dict[str, Any],
                                 public_id: str,
                                 folder: str = "api_requests",
                                 access_mode: str = "public",
                                 **kwargs) -> Dict[str, Any]:
        """
        Upload request data (like API payload) to Cloudinary.
        This is a wrapper around upload_json for semantic clarity.

        Args:
            request_data: Dictionary containing request data
            public_id: Unique identifier for the file
            folder: Folder path in Cloudinary
            access_mode: 'public' or 'authenticated'
            **kwargs: Additional arguments passed to upload_json

        Returns:
            Upload result dictionary from Cloudinary
        """
        return self.upload_json(request_data, public_id, folder, access_mode, **kwargs)

    def retrieve_data(self,
                      public_id: str,
                      resource_type: str = "raw",
                      as_json: bool = True) -> Union[str, Dict, list]:
        """
        Retrieve data from Cloudinary.

        Args:
            public_id: The public ID of the file (without folder path)
            resource_type: 'raw' for text/json files
            as_json: If True, parse as JSON; if False, return as string

        Returns:
            Parsed JSON data (if as_json=True) or raw text string
        """
        # First, get the resource details to construct the URL
        resource = cloudinary.api.resource(
            public_id, resource_type=resource_type)

        # Get the secure URL
        url = resource['secure_url']

        # Download the content
        response = requests.get(url)
        response.raise_for_status()

        content = response.text

        if as_json:
            return json.loads(content)
        else:
            return content

    def retrieve_by_url(self,
                        url: str,
                        as_json: bool = True) -> Union[str, Dict, list]:
        """
        Retrieve data from Cloudinary using the URL directly.

        Args:
            url: The Cloudinary URL of the file
            as_json: If True, parse as JSON; if False, return as string

        Returns:
            Parsed JSON data (if as_json=True) or raw text string
        """
        response = requests.get(url)
        response.raise_for_status()

        content = response.text

        if as_json:
            return json.loads(content)
        else:
            return content

    def list_files(self,
                   folder: str = "api_requests",
                   max_results: int = 10) -> Dict[str, Any]:
        """
        List all files in a specific folder.

        Args:
            folder: Folder path to list
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing list of resources
        """
        result = cloudinary.api.resources(
            resource_type="raw",
            type="upload",
            prefix=folder,
            max_results=max_results
        )
        return result

    def delete_file(self,
                    public_id: str,
                    resource_type: str = "raw") -> Dict[str, Any]:
        """
        Delete a file from Cloudinary.

        Args:
            public_id: The public ID of the file to delete
            resource_type: 'raw' for text/json files

        Returns:
            Deletion result dictionary
        """
        result = cloudinary.uploader.destroy(
            public_id, resource_type=resource_type)
        return result

    def update_json(self,
                    public_id: str,
                    new_data: Union[Dict, list],
                    folder: str = "api_requests",
                    merge: bool = True) -> Dict[str, Any]:
        """
        Update existing JSON data by merging or replacing.

        Args:
            public_id: Public ID of the existing JSON file
            new_data: New data to merge/replace with
            folder: Folder where the file exists
            merge: If True, merge with existing data; if False, replace completely

        Returns:
            Upload result of the updated file
        """
        # Retrieve existing data
        full_public_id = f"{folder}/{public_id}" if folder else public_id

        try:
            existing_data = self.retrieve_data(full_public_id, as_json=True)

            if merge and isinstance(existing_data, dict) and isinstance(new_data, dict):
                # Deep merge dictionaries
                updated_data = {**existing_data, **new_data}
            elif merge and isinstance(existing_data, list) and isinstance(new_data, list):
                # Extend lists
                updated_data = existing_data + new_data
            else:
                # Replace completely
                updated_data = new_data
        except:
            # File doesn't exist or can't be parsed, just use new data
            updated_data = new_data

        # Upload the updated data
        return self.upload_json(updated_data, public_id, folder, overwrite=True)


# Example usage and demonstration
if __name__ == "__main__":
    # Initialize with your Cloudinary credentials
    manager = CloudinaryDataManager(
        cloud_name="your_cloud_name",
        api_key="your_api_key",
        api_secret="your_api_secret"
    )

    # Example 1: Upload JSON data
    sample_data = {
        "user_id": 12345,
        "action": "login",
        "timestamp": "2024-01-15T10:30:00Z",
        "metadata": {
            "ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0"
        }
    }

    # Upload JSON
    upload_result = manager.upload_json(
        json_data=sample_data,
        public_id="user_login.json",
        folder="api_requests/logs"
    )
    print(f"✅ JSON uploaded: {upload_result['secure_url']}")

    # Example 2: Upload plain text
    text_content = "This is a log entry from the system"
    text_result = manager.upload_text(
        text_content=text_content,
        public_id="system_log.txt",
        folder="api_requests/logs"
    )
    print(f"✅ Text uploaded: {text_result['secure_url']}")

    # Example 3: Upload request data (semantic wrapper)
    request_payload = {
        "endpoint": "/api/users",
        "method": "POST",
        "body": {"name": "John", "email": "john@example.com"}
    }

    request_result = manager.upload_from_request_data(
        request_data=request_payload,
        public_id="api_request_123.json",
        folder="api_requests/payloads"
    )
    print(f"✅ Request data uploaded: {request_result['secure_url']}")

    # Example 4: Retrieve the data back
    retrieved_data = manager.retrieve_data(
        public_id="api_requests/logs/user_login.json",
        as_json=True
    )
    print(f"\n📥 Retrieved data: {json.dumps(retrieved_data, indent=2)}")

    # Example 5: Retrieve by URL
    url = upload_result['secure_url']
    data_from_url = manager.retrieve_by_url(url, as_json=True)
    print(f"\n📥 Data from URL: {data_from_url['user_id']}")

    # Example 6: List all files in a folder
    files = manager.list_files(folder="api_requests/logs", max_results=5)
    print(f"\n📁 Files in folder: {len(files.get('resources', []))}")

    # Example 7: Update existing JSON
    updated = manager.update_json(
        public_id="user_login.json",
        new_data={"status": "completed", "response_time_ms": 234},
        folder="api_requests/logs",
        merge=True
    )
    print(f"\n🔄 Updated JSON: {updated['secure_url']}")

    # Example 8: Delete a file (uncomment to use)
    # delete_result = manager.delete_file("api_requests/logs/system_log.txt")
    # print(f"🗑️ Deleted: {delete_result}")
