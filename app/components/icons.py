import os
from enum import Enum

from PySide6.QtCore import QFile, QObject, QRect, QRectF, Qt
from PySide6Addons import FluentIconBase, Theme, getIconColor, isDarkTheme

# pyside6-rcc "app/common/resource/resource.qrc" -o "app/common/resource/resource_rc.py"

NO_DARK_FILE = ['logo.png']


class FileIcon(FluentIconBase, Enum):
    LOGO = 'logo.png'
    LOGO_SPLASH_SCREEN = 'logo-splash-screen.png'
    IMAGE_PLACEHOLDER = 'no-image-placeholder.jpg'
    # IMAGE_PLACEHOLDER_SVG = 'no-image-placeholder.svg'
    YOUTUBE_LOGO = 'brand/youtube.png'
    INSTAGRAM_LOGO = 'brand/instagram.png'
    FACEBOOK_LOGO = 'brand/facebook.png'
    TIKTOK_LOGO = 'brand/tiktok.png'
    DOUYIN_LOGO = 'brand/douyin.png'
    KUAISHOU_LOGO = 'brand/kuaishou.png'
    # Drama
    DRAMABOX_LOGO = 'drama/dramabox-logo.png'
    REELSHORT_LOGO = 'drama/reelshort-logo.png'
    DRAMABITE_LOGO = 'drama/dramabite-logo.png'
    SHORTMOVS_LOGO = 'drama/shortmovs-logo.png'
    RUSHSHORTSTV_LOGO = 'drama/rushshortstv-logo.png'
    STARDUSTTV_LOGO = 'drama/stardusttv-logo.png'
    FLICKREELS_LOGO = 'drama/flickreels-logo.png'
    # icons
    DOWNLOAD = 'icons/download.png'
    SETTINGS = 'icons/settings.png'
    VIDEO_DOWNLOAD = 'icons/video-download.png'
    DOCUMENTS = 'icons/documents.png'
    VIEW_FILE = 'icons/view-file.png'
    VIDEO = 'icons/video.png'
    VIDEO_FILE = 'icons/video-file.png'

    def path(self, theme=Theme.AUTO):
        type_icon = getIconColor(theme)
        type_icon = '-dark' if type_icon == 'white' else ''
        name, ext = os.path.splitext(self.value)
        file = f'./app/common/images/{name}{type_icon}{ext}'
        # file = f':/assets/images/{name}{type_icon}{ext}'
        if type_icon == '-dark' and not QFile(file).exists():
            file = f'./app/common/images/{self.value}'
            # file = f':/assets/images/{self.value}'

        return file
        # return f':/assets/images/{self.value}'
