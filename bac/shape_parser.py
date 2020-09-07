# -*- coding: utf-8 -*-
# SPDX-License-Identifier: BSD-3-Clause
# Copyright © 2020, GoodData(R) Corporation. All rights reserved.


class ShapeParser(object):
    """
    Parses the output shape into a fake JSON response.

    Processes the AWS API response 'output-shape' into a
    fake response (dummy response) JSON object.
    """
    def parse(self, shape):
        """Start the parsing process on received shape."""
        dummy_response = self._parse_shape(shape)
        return dummy_response

    def _parse_shape(self, shape):
        shape_type = shape.type_name
        if shape_type == 'list':
            return self._handle_list(shape)
        if shape_type == 'structure':
            return self._handle_structure(shape)
        if shape_type == 'map':
            return self._handle_map(shape)
        return self._default_handle(shape)

    def _default_handle(self, shape):
        # Return shape type as dummy value of scalar type.
        return '%s:%s' % (shape.name, shape.type_name)

    def _handle_list(self, shape):
        member_shape = shape.member
        parsed = []
        parsed.append(self._parse_shape(member_shape))
        return parsed

    def _handle_structure(self, shape):
        parsed = {}
        member_shapes = shape.members
        for name, member in member_shapes.items():
            parsed[name] = self._parse_shape(member)
        return parsed

    def _handle_map(self, shape):
        parsed = {}
        key_shape = shape.key
        value_shape = shape.value
        key = self._parse_shape(key_shape)
        value = self._parse_shape(value_shape)
        parsed[key] = value
        return parsed
