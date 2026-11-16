# piwigo-batch-uploader

Batch upload images to a self-hosted [Piwigo](https://piwigo.org/) gallery from a CSV.

Creates albums named after the `Carton` column, sets them private, sets a photo privacy level, optionally shares them with a group, uploads each image with a composite description, and optionally rotates based on keywords in the Description field.

## Requirements

- Python 3.8+
- `requests`
- `Pillow`

## Install dependencies

Prefer the OS package installer (installs `python3-pillow` / `python3-pil` and `python3-requests`):

```bash
./dependencies.sh
```

Or the pip fallback:

```bash
pip install -r dependencies.txt
```

Or install the project itself:

```bash
pip install -e .
```

## Usage

```bash
python run.py --config piwigo-config.json --csv data.csv
python run.py --config piwigo-config.json --csv data.csv --dry-run
python run.py --config piwigo-config.json --csv data.csv --share-with-group othergroup
```

After `pip install -e .` you can also run:

```bash
piwigo-batch-uploader --config piwigo-config.json --csv data.csv
```

### Config

Copy [piwigo-config.example.json](piwigo-config.example.json) to `piwigo-config.json` and fill in `base_url`, `api_key_id`, and `api_key`. `share_with_group` defaults to `curators` and `privacy_level` defaults to `everybody` if omitted.

### CSV columns

`Description,Date,#,Code,Location,Carton,Comment,Frame,Brand,Scanned,File,Date Film,Reel,Serial,Path`

- `Description` → photo title
- `Path` → image file
- `Carton` → album name
- `Location` → album description (`Location: …`)
- Remaining non-blank columns → multi-line photo description

### Rotation (case-insensitive, from Description)

1. `rotate right` → 90° clockwise
2. `rotate 180` → 180°
3. `(portrait` → 90° counter-clockwise
4. otherwise → no rotation

Rotation is always applied to a temporary copy; the original file is never modified.

## Groups and permissions

See [piwigo.md](piwigo.md) for the curator group, collections, and comments. `--share-with-group` defaults to `curators`. `--privacy-level` defaults to everybody.

## License

GNU General Public License v3 or later (see `license.txt`).

