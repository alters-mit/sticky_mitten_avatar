from argparse import ArgumentParser
from pathlib import Path
import json
from distutils import file_util
from tdw.librarian import ModelLibrarian, ModelRecord
from tdw.backend.platforms import UNITY_TO_SYSTEM
from tdw.asset_bundle_creator import AssetBundleCreator


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--name", type=str,
                        help="The name of the prefab in ~/asset_bundle_creator/Assets/Resources/prefab")
    parser.add_argument("--lib", type=str, default="containers.json", help="The name of the local library.")
    args = parser.parse_args()

    # Load the local library.
    root_dest = Path.home().joinpath("sticky_mitten_avatar/sticky_mitten_avatar")
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
    record_path = a.create_record(args.name, 2886585, "box", 1, urls)
    record = ModelRecord(json.loads(record_path.read_text(encoding="utf-8")))

    # Add the record.
    r = lib.get_record(record.name)
    if r is None:
        lib.add_or_update_record(record=record, overwrite=False, write=True)
    # Update the URLs.
    for p in record.urls:
        dest_dir = f"../asset_bundles/{p}"
        dd = root_dest.joinpath(f"asset_bundles/{p}")
        if not dd.exists():
            dd.mkdir(parents=True)
        record.urls[p] = f"../asset_bundles/{p}/{record.name}"
    # Copy the asset bundles.
    for p in UNITY_TO_SYSTEM:
        src = src_asset_bundles[p]
        dest = root_dest.joinpath(f"asset_bundles/{UNITY_TO_SYSTEM[p]}/{record.name}")
        file_util.copy_file(str(src.resolve()), str(dest.resolve()))
