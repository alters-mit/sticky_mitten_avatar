from argparse import ArgumentParser
from pathlib import Path
import json
from distutils import file_util
from tdw.librarian import ModelLibrarian, ModelRecord
from tdw.backend.platforms import UNITY_TO_SYSTEM
from tdw.asset_bundle_creator import AssetBundleCreator


"""
Use this script to add create an asset bundle from a prefab and add it to a library in this repo. See: 
 [AssetBundleCreator](https://github.com/threedworld-mit/tdw/blob/master/Documentation/python/asset_bundle_creator.md)
"""


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--name", type=str,
                        help="The name of the prefab in ~/asset_bundle_creator/Assets/Resources/prefab")
    parser.add_argument("--lib", type=str, default="containers", help="The name of the local library.")
    args = parser.parse_args()

    # Load the local library.
    root_dest = Path.home().joinpath("../sticky_mitten_avatar/sticky_mitten_avatar")
    lib_path = str(root_dest.joinpath(f"metadata_libraries/{args.lib}.json").resolve())
    lib = ModelLibrarian(library=lib_path)

    # Create asset bundles.
    a = AssetBundleCreator()
    src_paths = a.prefab_to_asset_bundle(Path.home().joinpath("asset_bundle_creator/Assets/Resources/prefab"),
                                         model_name=args.name)
    src_asset_bundles = dict()
    for q in src_paths:
        src_asset_bundles[q.parts[-2]] = q

    # Parse the URLs.
    urls = a.get_local_urls(src_paths)

    # Create the metadata record.
    record_path = a.create_record(args.name, 2886585, "container", 1, urls)
    record = ModelRecord(json.loads(record_path.read_text(encoding="utf-8")))

    # Add the record.
    r = lib.get_record(record.name)
    lib.add_or_update_record(record=record, overwrite=False if r is None else True, write=True)
    # Make the URLs relative paths.
    temp = dict()
    for p in record.urls:
        dest_dir = f"../asset_bundles/{p}"
        dd = root_dest.joinpath(f"asset_bundles/{p}")
        if not dd.exists():
            dd.mkdir(parents=True)
        temp[p] = f"../asset_bundles/{p}/{record.name}"
    record.urls = temp
    lib.add_or_update_record(record=record, overwrite=True, write=True)
    # Copy the asset bundles.
    for p in UNITY_TO_SYSTEM:
        src = src_asset_bundles[p]
        dest = root_dest.joinpath(f"asset_bundles/{UNITY_TO_SYSTEM[p]}/{record.name}")
        file_util.copy_file(str(src.resolve()), str(dest.resolve()))
