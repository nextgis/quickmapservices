# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Common Plugins settings

 NextGIS
                             -------------------
        begin                : 2014-10-31
        git sha              : $Format:%H$
        copyright            : (C) 2014 by NextGIS
        email                : info@nextgis.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings


class PluginSettings():

    _company_name = 'NextGIS'
    _product = 'QuickMapServices'

    @classmethod
    def product_name(cls):
        return cls._product

    @classmethod
    def get_settings(cls):
        return QSettings(cls._company_name, cls._product)

    @classmethod
    def default_tile_layer_conn_count(cls):
        return cls.get_settings().value('tile_layer/default_connection_count', 4, int)

    @classmethod
    def set_default_tile_layer_conn_count(cls, int_val):
        cls.get_settings().setValue('tile_layer/default_connection_count', int_val)

    @classmethod
    def show_messages_in_bar(cls):
        return cls.get_settings().value('show_messages_in_bar', True, bool)

    @classmethod
    def set_show_messages_in_bar(cls, bool_val):
        return cls.get_settings().setValue('show_messages_in_bar', bool_val)

    @classmethod
    def move_to_layers_menu(cls):
        return cls.get_settings().value('move_to_layers_menu', False, bool)

    @classmethod
    def set_move_to_layers_menu(cls, bool_val):
        return cls.get_settings().setValue('move_to_layers_menu', bool_val)

    @classmethod
    def enable_otf_3857(cls):
        return cls.get_settings().value('enable_otf_3857', False, bool)

    @classmethod
    def set_enable_otf_3857(cls, bool_val):
        return cls.get_settings().setValue('enable_otf_3857', bool_val)
