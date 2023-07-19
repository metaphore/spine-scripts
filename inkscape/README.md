# Inkscape to Spine

## Installation

* To download, right click each of these files and choose `Save As`:
  * [LayersToSpine.inx](https://github.com/EsotericSoftware/spine-scripts/raw/master/inkscape/LayersToSpine.inx)
  * [LayersToSpine.py](https://github.com/EsotericSoftware/spine-scripts/raw/master/inkscape/LayersToSpine.py)
  - [ObjectsToSpine.inx](https://github.com/EsotericSoftware/spine-scripts/raw/master/inkscape/ObjectsToSpine.inx)
  * [ObjectsToSpine.py](https://github.com/EsotericSoftware/spine-scripts/raw/master/inkscape/ObjectsToSpine.py)
  * [PathsToSpine.inx](https://github.com/EsotericSoftware/spine-scripts/raw/master/inkscape/PathsToSpine.inx)
  * [PathsToSpine.py](https://github.com/EsotericSoftware/spine-scripts/raw/master/inkscape/PathsToSpine.py)
* Move the files to the Inkscape extensions directory (eg `$HOME/.config/inkscape/extensions`).
* Restart Inkscape.

## Usage

After installation, choose `Spine` under the `Extensions` menu.

- `Spine Export - Layers` - for each leaf layer, an image will be written to the specified output directory. By default, a Spine JSON file will be generated in the output directory and images will be output to the `./images` directory within it.

- `Spine Export - Objects` - works just like with the layers, but it exports only the selected objects and groups. The name of each image is the `id` field of the corresponding SVG object (you can edit object properties in the XML Editor window - `CTRL`+`SHIFT`+`X`).

- `Spine Export - Paths` - a Spine JSON file containing the Inkscape paths will be generated.

The Spine JSON files can be [imported](http://esotericsoftware.com/spine-import) into Spine.
