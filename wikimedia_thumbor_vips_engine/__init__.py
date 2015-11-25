#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com timehome@corp.globo.com
# Copyright (c) 2015 Wikimedia Foundation

# VIPS engine
# Very minimal, only supports resizing and cropping, no filters

import gi
gi.require_version('Vips', '8.0')
from gi.repository import Vips

from thumbor.engines import BaseEngine


class Engine(BaseEngine):
    def create_image(self, buffer):
        return Vips.Image().new_from_buffer(data=buffer, option_string=None)

    def read(self, extension=None, quality=None):
        return self.image.write_to_buffer(format_string=extension)

    def resize(self, width, height):
        # In the context of thumbnailing we're fine with a resize
        # that always conserves the original aspect ratio, which is
        # what vips_resize() does.
        #
        # This is how Thumbor behaves for basic AxB requests anyway,
        # it resizes while keeping the aspect ratio first, then calls
        # crop().
        self.image = self.image.resize(width / self.size[0])

    def crop(self, left, top, right, bottom):
        self.image = self.image.extract_area(
            left,
            top,
            right - left,
            bottom - top
        )

    def should_run(self, extension, buffer):
        if extension != '.png':
            return False

        image = self.create_image(buffer)
        pixels = image.width * image.height

        if self.context.config.VIPS_ENGINE_MIN_PIXELS is None:
            return True
        else:
            if pixels > self.context.config.VIPS_ENGINE_MIN_PIXELS:
                return True

        return False

    @property
    def size(self):
        return self.image.width, self.image.height
