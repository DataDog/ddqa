# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from textual.widgets import Static


class Placeholder(Static):
    DEFAULT_CSS = """
    Placeholder {
        content-align: center middle;
    }
    """

    def __init__(self, *args, width_factor: float = 1.00, height_scale: float = 0.40, **kwargs):
        super().__init__(*args, **kwargs)

        self.__width_factor = width_factor
        self.__height_scale = height_scale

    def on_mount(self):
        import shutil
        from importlib.resources import files
        from io import BytesIO

        from PIL import Image
        from rich.text import Text

        ascii_chars = '@S#%?*+;:, '
        buckets = 256 // (len(ascii_chars) - 1)

        with BytesIO(files('ddqa.data').joinpath('logo.png').read_bytes()) as buffer, Image.open(buffer) as raw_image:
            old_width, old_height = raw_image.size
            new_width = int(shutil.get_terminal_size()[0] // self.__width_factor)
            new_height = int(old_height // (old_width / (new_width * self.__height_scale)))

            # Resize and convert to grayscale
            image = (
                raw_image
                # Account for transparency in our PNG logo palette image
                .convert('RGBA')
                # Convert to grayscale
                .convert('L')
                # Resize to fit terminal dimensions
                .resize((new_width, new_height))
            )

            pixels = ''.join(ascii_chars[pixel_value // buckets] for pixel_value in image.getdata())
            num_pixels = len(pixels)

            self.update(
                Text(
                    '\n'.join(pixels[index : index + new_width] for index in range(0, num_pixels, new_width)),
                    # https://www.datadoghq.com/about/resources/#datadog-purple
                    style='rgb(99,44,166)',
                )
            )
