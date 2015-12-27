#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
# Copyright (c) 2015 Wikimedia Foundation

# VIPS engine

import errno
import os
from tempfile import NamedTemporaryFile

from wikimedia_thumbor_base_engine import BaseWikimediaEngine


BaseWikimediaEngine.add_format(
    'image/tiff',
    '.tiff',
    lambda buffer: (
        buffer.startswith('II*\x00') or buffer.startswith('MM\x00*')
    )
)


class Engine(BaseWikimediaEngine):
    def should_run(self, extension, buffer):
        if extension not in ('.png', '.tiff'):
            return False

        self.context.vips = {}

        self.prepare_temp_files(buffer)

        command = [
            self.context.config.VIPS_PATH,
            'im_header_int',
            'Xsize',
            self.source.name
        ]

        width = int(self.command(command))
        self.context.vips['width'] = width

        command = [
            self.context.config.VIPS_PATH,
            'im_header_int',
            'Ysize',
            self.source.name
        ]

        height = int(self.command(command))
        self.context.vips['height'] = height

        pixels = width * height

        if self.context.config.VIPS_ENGINE_MIN_PIXELS is None:
            return True
        else:
            if pixels > self.context.config.VIPS_ENGINE_MIN_PIXELS:
                return True

        self.cleanup_temp_files()

        return False

    def create_image(self, buffer):
        try:
            extension = self.context.request.extension
        except AttributeError:
            # If there is no extension in the request, it means that we
            # are serving a cached result. In which case no VIPS processing
            # is required.
            return super(Engine, self).create_image(buffer)

        self.original_buffer = buffer

        try:
            source = "%s[page=%d]" % (
                self.source.name,
                self.context.request.page - 1
            )
        except AttributeError:
            source = self.source.name

        # Replace the extension-less destination by one that has the
        # png extension. This is necessary because the vips command line
        # figures out the export format based on the destination filename.
        # It doesn't have any option to specify it.

        try:
            os.remove(self.destination.name)
        except OSError, e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise e

        self.destination = NamedTemporaryFile(delete=False, suffix=extension)

        resize_factor = (
            float(self.context.request.width)
            /
            float(self.context.vips['width'])
        )

        # Send a resized (but not cropped) image to PIL
        command = [
            self.context.config.VIPS_PATH,
            'resize',
            source,
            self.destination.name,
            "%f" % resize_factor
        ]
        result = self.exec_command(command)
        self.extension = extension

        return super(Engine, self).create_image(result)

    def read(self, extension=None, quality=None):
        if extension == '.tiff' and quality is None:
            # We're saving the source, let's save the original
            return self.original_buffer

        # Beyond this point we're saving the result
        if extension == '.tiff':
            if self.context.request.extension == '.png':
                extension = '.png'
            else:
                extension = '.jpg'

        return super(Engine, self).read(extension, quality)
