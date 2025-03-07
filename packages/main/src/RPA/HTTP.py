import logging
from urllib.parse import urlparse
from typing import Any, Union
from pathlib import Path

from RequestsLibrary import RequestsLibrary
from RPA.FileSystem import FileSystem
from RPA.core.notebook import notebook_file


class HTTP(RequestsLibrary):
    """RPA Framework HTTP library that extends functionality of RequestsLibrary,
    for more information see: https://github.com/MarketSquare/robotframework-requests
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    def __init__(self, *args, **kwargs) -> None:
        RequestsLibrary.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.fs = FileSystem()
        self.session_alias_prefix = "rpasession_alias."
        self.current_session_alias = None

    def http_get(
        self,
        url: str,
        target_file: str = None,
        verify: Union[bool, str] = True,
        force_new_session: bool = False,
        overwrite: bool = False,
        stream: bool = False,
        **kwargs,
    ) -> dict:
        """
        A helper method for ``Get Request`` that will create a session, perform GET
        request, and store the target file, if set by the ``target_file`` parameter.

        The old session will be used if the URL scheme and the host are the same as
        previously, e.g., 'https://www.google.fi' part of the URL.

        ``url`` target URL for GET request

        ``target_file`` filepath to save request content, default ``None``

        ``verify`` if SSL verification should be done, default ``True``,
        a CA_BUNDLE path can also be provided

        ``force_new_session`` if new HTTP session should be created, default ``False``

        ``overwrite`` used together with ``target_file``, if ``True`` will overwrite
        the target file, default ``False``

        ``stream`` if ``False``, the response content will be immediately downloaded

        Returns request response.
        """
        uc = urlparse(url)

        http_host = f"{uc.scheme}://{uc.netloc}"
        request_alias = f"{self.session_alias_prefix}{uc.scheme}{uc.netloc}"
        url_path = url.replace(http_host, "")

        if force_new_session or not self.session_exists(request_alias):
            self.logger.info("Creating a new HTTP session")
            self.create_session(request_alias, http_host, verify=verify)
        else:
            self.logger.info("Using already existing HTTP session")

        self.current_session_alias = request_alias
        response = self.get_on_session(request_alias, url_path, stream=stream, **kwargs)

        if target_file is not None:
            self._create_or_overwrite_target_file(
                target_file, response.content, overwrite
            )

        return response

    def _create_or_overwrite_target_file(
        self,
        path: str,
        response: Any,
        overwrite: bool,
    ) -> None:
        CHUNK_SIZE = 32768
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        file_exists = Path(path).is_file()
        if not file_exists or (file_exists and overwrite):
            with open(path, "wb") as f:
                for chunk in response.iter_content(CHUNK_SIZE):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
        notebook_file(path)

    def get_current_session_alias(self) -> str:
        """Get request session alias that was used with the ``HTTP Get`` keyword.

        Return name of session alias.
        """
        return self.current_session_alias

    def download(
        self,
        url: str,
        target_file: str = None,
        verify: Union[bool, str] = True,
        force_new_session: bool = False,
        overwrite: bool = False,
        stream: bool = False,
        **kwargs,
    ) -> dict:
        """An alias for the ``HTTP Get`` keyword.

        The difference in use is that the URL is always downloaded based on
        the URL path (even without ``target_file``). If there is a filename
        in the path, then that is used as ``target_file`` to save to. By default,
        the filename will be "downloaded.html".

        ``url`` target URL for GET request

        ``target_file`` filepath to save request content, default ``None``

        ``verify`` if SSL verification should be done, default ``True``,
        a CA_BUNDLE path can also be provided

        ``force_new_session`` if new HTTP session should be created, default ``False``

        ``overwrite`` used together with ``target_file``, if ``True`` will overwrite
        the target file, default ``False``

        ``stream`` if ``False``, the response content will be immediately downloaded
        """
        response = self.http_get(
            url,
            verify=verify,
            force_new_session=force_new_session,
            overwrite=overwrite,
            stream=stream,
            **kwargs,
        )

        dirname = Path()
        filename = None

        if target_file is not None:
            target = Path(target_file)
            if target.is_dir():
                dirname = target
            else:
                dirname = target.parent
                filename = target.name

        if filename is None:
            filename = urlparse(url).path.rsplit("/", 1)[-1] or "downloaded.html"

        self._create_or_overwrite_target_file(dirname / filename, response, overwrite)

        return response
