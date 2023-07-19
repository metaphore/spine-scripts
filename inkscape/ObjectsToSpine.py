#!/usr/bin/env python
# coding=utf-8
"""
Spine export for Inkscape

Export each selected object in the current document to individual PNG file
and generate a Spine JSON file to import.
https://esotericsoftware.com/spine-json-format

Original hosting location:
https://github.com/jleclanche/inkscape-spine-exporter
"""

import os
import inkex
import json
import subprocess

INKSCAPE_LABEL = "{%s}label" % (inkex.NSS["inkscape"])

def parse_css_style(style):
    ret = {}
    for directive in style.split(";"):
        directive = directive.strip()
        if not directive:
            continue
        k, v = directive.split(":")
        ret[k.lower()] = v.lower()
    return ret


class SpineExporter(inkex.EffectExtension):
    def __init__(self):
        inkex.EffectExtension.__init__(self)
        self.arg_parser.add_argument(
            "--outdir",
            action="store",
            type=str,
            dest="outdir",
            default="~",
            help="Path to the export directory",
        )
        self.arg_parser.add_argument(
            "--skeleton-name",
            action="store",
            type=str,
            dest="skel_name",
            default=None,
            help="Name of the exported skeleton",
        )
        self.arg_parser.add_argument(
            "--dpi",
            action="store",
            type=float,
            dest="dpi",
            default=90.0,
            help="Resolution to export at",
        )
        self.arg_parser.add_argument(
            "--json",
            type=inkex.Boolean,
            dest="json",
            help="Create a Spine JSON file",
        )
        self.arg_parser.add_argument(
            "--pretty-print",
            type=inkex.Boolean,
            dest="pretty",
            help="Pretty-print the JSON file",
        )
        self.arg_parser.add_argument(
            "--center-content",
            type=inkex.Boolean,
            dest="center_slots",
            help="Center exported content at zero point",
        )
        # self.arg_parser.add_argument(
        #     "--merge",
        #     action="store",
        #     type=str,
        #     dest="merge",
        #     default="",
        #     help="Spine JSON file to merge with",
        # )

        # The default root bone
        self.root_bone = {"name": "root"}
        self.bone_coords = {}

    @property
    def root(self):
        return self.document.getroot()

    @property
    def friendly_name(self):
        docname = self.root.xpath("//@sodipodi:docname", namespaces=inkex.NSS)
        if docname:
            return docname[0].replace(".svg", "")
        return self.root.attrib["id"]

    @property
    def layers(self):
        xpath = "./svg:g[@inkscape:groupmode='layer']"

        def get_layers(e):
            ret = []
            sublayers = e.xpath(xpath, namespaces=inkex.NSS)
            if sublayers:
                for sublayer in sublayers:
                    ret += get_layers(sublayer)
            else:
                ret.append(e)
            return ret

        return get_layers(self.root)

    @property
    def drawing_size(self):
        x, y, width, height = self.get_bounding_box(self.root.attrib["id"])
        return width, height

    def get_bounding_box(self, id):
        command = (
            "inkscape",
            self.options.input_file,
            "--query-id",
            str(id),
            "--query-x",
            "--query-y",
            "--query-width",
            "--query-height",
        )
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        stdout = process.stdout
        # inkex.utils.debug(stdout)
        x, y, width, height = stdout.split("\n")[0:-1]
        return float(x), float(y), float(width), float(height)

    def autocrop_in_place(self, path):
        from PIL import Image

        im = Image.open(path)
        bbox = im.getbbox()
        cropped = im.crop(bbox)
        cropped.save(path)
        return im.size, bbox

    def get_default_struct(self):
        return {
            "skeleton": {},
            "bones": [self.root_bone],
            "slots": [],
            "skins": {"default": {}},
            "animations": {"animation": {}},
        }

    # def get_default_struct(self):
    #     """
    #     If the merge option was specified, attempt to load the given file
    #     as JSON and return its contents.
    #     Otherwise, return a default Spine structure.
    #     """
    #     default = self.options.merge
    #     if default:
    #         try:
    #             with open(default, "r") as f:
    #                 ret = json.load(f)
    #             self.root_bone = ret["bones"][0]
    #         except Exception:
    #             inkex.errormsg("%r is not a valid Spine JSON file." % (default))
    #             raise
    #     else:
    #         ret = {
    #             "skeleton": {},
    #             "bones": [self.root_bone],
    #             "slots": [],
    #             "skins": {"default": {}},
    #             "animations": {"animation": {}},
    #         }
    #     return ret

    def _get_obj(self, struct, name):
        """
        Find a named slot or bone in a spine structure
        """
        for obj in struct:
            if obj["name"] == name:
                return obj

    def coords_to_spine(self, left, top, width, height):
        global_width, global_height = self.drawing_size
        bottom = height + top
        x = 0.5 * width - (global_width * 0.5) + left
        y = (global_height - top - bottom) / 2
        return x, y, width, height

    def merge_spine_skin(self, struct, name, bbox):
        x, y, width, height = self.coords_to_spine(*bbox)

        slot = self._get_obj(struct["slots"], name)
        if slot:
            # We found a slot, add its parent's coordinates to x/y
            bone_x, bone_y = self.bone_coords[slot["bone"]]
        else:
            bone_x, bone_y = self.bone_coords[self.root_bone["name"]]

        x += bone_x
        y += bone_y

        # You still here? Well that was fun but doesn't actually work :-)
        # Damn Spine and its relative coordinate imports. Let's just hard-merge.
        if slot:
            # Revert existing slots
            x, y, width, height = self.coords_to_spine(*bbox)
            # Reset the slot's bone to root... =/
            # slot["bone"] = self.root_bone["name"]
            return

        # fin

        struct["skins"]["default"][name] = {
            name: {"x": x, "y": y, "width": width, "height": height},
        }

    def merge_spine_slot(self, struct, name):
        """
        Iterate over a Spine skeleton and add a bone only if it does not
        already exist.
        """
        slot = self._get_obj(struct["slots"], name)
        if slot is None:
            struct["slots"].append(
                {"name": name, "bone": self.root_bone["name"], "attachment": name}
            )
            return True

    def center_spine_slots(self, struct):
        skin = struct["skins"]["default"]

        x_min = float('+inf')
        x_max = float('-inf')
        y_min = float('+inf')
        y_max = float('-inf')
        for prop_name, prop_value in skin.items():
            slot = prop_value[prop_name]
            center_x = slot.get("x", 0.0)
            center_y = slot.get("y", 0.0)
            half_width = slot.get("width", 0.0) * 0.5
            half_height = slot.get("height", 0.0) * 0.5
            x_min = min(x_min, center_x - half_width)
            x_max = max(x_max, center_x + half_width)
            y_min = min(y_min, center_y - half_height)
            y_max = max(y_max, center_y + half_height)

        bb_center_x = (x_min + x_max) * 0.5
        bb_center_y = (y_min + y_max) * 0.5

        # inkex.utils.debug("BB center: " + str(bb_center_x) + " " + str(bb_center_y))

        for prop_name, prop_value in skin.items():
            slot = prop_value[prop_name]
            slot["x"] = slot.get("x", 0.0) - bb_center_x
            slot["y"] = slot.get("y", 0.0) - bb_center_y

    def effect(self):
        selected_objects = self.svg.selected
        if len(selected_objects) == 0:
            inkex.errormsg("Nothing is selected.")
            return

        outdir = os.path.expanduser(self.options.outdir)
        imagedir = os.path.join(outdir, "images")
        if not os.path.exists(imagedir):
            os.makedirs(imagedir)

        spine_struct = self.get_default_struct()
        spine_struct["skeleton"]["images"] = imagedir

        for bone in spine_struct["bones"]:
            # Cache the World coordinates of every bone
            x, y = bone.get("x", 0), bone.get("y", 0)
            name = bone.get("parent")
            while name:
                parent = self._get_obj(spine_struct["bones"], name)
                x += parent.get("x", 0)
                y += parent.get("y", 0)
                name = parent.get("parent")

            self.bone_coords[bone["name"]] = x, y

        for obj in selected_objects:
            id = obj.get_id()
            label = obj.attrib.get(INKSCAPE_LABEL, id)

            outfile = os.path.join(imagedir, "%s.png" % label)

            # Render the object.
            command = (
                "inkscape",
                self.options.input_file,
                "--export-filename",
                outfile,
                "--export-id-only",
                "--export-id",
                id,
                "--export-dpi",
                str(self.options.dpi),
            )
            subprocess.run(command, capture_output=True, check=True)

            bbox = self.get_bounding_box(id)
            self.merge_spine_skin(spine_struct, label, bbox)
            # Slot merge must come after the skin merge because we need the
            # original data.
            self.merge_spine_slot(spine_struct, label)

        if self.options.json:

            if self.options.center_slots:
                self.center_spine_slots(spine_struct)

            # If user didn't specify the skeleton name, use the document name instead.
            skel_name = self.options.skel_name
            if not skel_name or skel_name.isspace():
                skel_name = self.friendly_name
            path = os.path.join(outdir, "%s.json" % skel_name)
            if self.options.pretty:
                args = {"separators": (",", ": "), "indent": 4}
            else:
                args = {"separators": (",", ":")}

            with open(path, "w") as f:
                json.dump(spine_struct, f, **args)



if __name__ == '__main__':
    inkex.localization.localize()
    SpineExporter().run()
