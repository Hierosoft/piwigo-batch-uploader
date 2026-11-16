# Piwigo setup for the batch uploader

The uploader creates one private album per `Carton` value. It grants the group **curators** access to each album, and sets each photo's privacy level to **Everybody**. Public visitors cannot see those albums. A logged-in curator can see them, build collections, and publish a permanent link to a collection.

## Main setup

The API user that owns the key in `piwigo-config.json` must be an administrator (or webmaster). Album creation (`pwg.categories.add`) is admin-only. A normal user cannot create albums through the API.

To promote that user:

1. Log in as an existing administrator.
2. **Users → Manage.** Edit the uploader user (the one that owns the API key).
3. Set **Status** to **Administrator** (or Webmaster). Save.

There is no friend-request system. “Adding the curator as a friend” is an admin action: set that user’s **Privacy level** to **Friends**. The curator does not accept anything. The change takes effect on their next page load.

1. Log in as an administrator.
2. **Users → Groups.** Create a group named `curators`. Do not name it `Friends` — that collides with the privacy level.
3. **Users → Manage.** Create the curator user (example: `alice`). Set **Privacy level** to **Friends**. Add `alice` to the `curators` group. Leave the status as a normal user (not admin).
4. Install and activate **User Collections**. In its Configuration tab, enable **allow public collections**. That is what creates the permanent share link.
5. **Configuration → Options → Comments.** Check **Activate comments**. Leave **Comments for all** unchecked so only logged-in users can comment. Uncheck **Email address is mandatory**. Piwigo shows the username on a comment; the email is visible only to administrators.<grok type="render_inline_citation" citation_id="482" />
6. Optional but recommended: install **Comments Access Manager**. With **Comments for all** off, restrict commenting to the `curators` group. Then only admins and curators can comment. Without that plugin, any logged-in user who can see a photo can comment.
7. Upload:

```bash
python run.py --config piwigo-config.json --csv data.csv
```

The uploader shares each album with `curators` by default. Override with `--share-with-group othername` or set `share_with_group` in the config JSON. Pass `--share-with-group ""` to skip.

### Why the group is required

A private album is invisible until someone is granted access. Privacy level is a second filter, applied only after album access is granted. Setting the curator to Friends does nothing by itself: without the `curators` group (or a direct user grant), the curator sees no albums and no photos. That is what “without this the curator sees nothing” means.

With both in place, the curator sees every photo the uploader adds (default level Everybody, and Friends covers that).

### What the curator does

- Logs in, browses the private albums, and adds photos to a collection (star icon).
- Opens **Collections**, opens a collection, and uses the share icon. The link is permanent until cancelled. Optional: custom URL end, password, expiry.
- The link shows only that collection. It does not open the album. A visitor who is not logged in sees nothing else.
- Comments on the photos in the collection, if comments are active. Comments are visible to anyone who can open the photo (including through the collection link).

### Renaming photos

A non-admin cannot rename an existing photo. Comments are the practical alternative. If rename is required, either make the curator an admin, or install Community plus Admin Tools and transfer photo ownership (`added_by`) so the curator can edit photos they own. That is extra setup and not the default.

## Manual upload (web interface)

The same result as the batch uploader, done by hand. The uploader user must be an administrator (see Main setup). The curator must already be in the `curators` group with privacy level Friends, and User Collections must have **allow public collections** enabled.

1. Log in as the uploader (admin).
2. **Administration → Albums → Manage.** Create a new album. Leave it **private**. Public albums are visible to anyone who can reach the gallery.
3. Open the album’s permissions (the lock or Permissions action). Grant the group **curators** access. Without this, the curator sees no albums and no photos.
4. **Administration → Photos → Add.** Choose the album, then upload the images. After upload, set each photo’s **privacy level** to **Everybody** (Photos → Batch Manager, or the photo edit page). Everybody is required so collection share links show the photos. Friends-level photos stay hidden on a public collection link.
5. Log out. Log in as the curator. The private album appears. Add photos to a collection (star icon), open **Collections**, and use the share icon. The permanent link shows only that collection. A visitor who is not logged in sees nothing else.

New albums do not inherit group permissions. Grant `curators` on each album you create by hand, the same way the batch uploader does for each Carton album.

## Upload size limits

The uploader sends each image in one POST. Assume a max image size of **12 MB**. Raise the web server and PHP limits above that, or the server returns `413 Request Entity Too Large` before Piwigo sees the file.

### Find the running PHP-FPM version

The version in the path must match the FPM service that serves the site. List installed versions and running services:

```bash
ls /etc/php
systemctl list-units --type=service 'php*-fpm*'
```

A typical Debian service is `php8.4-fpm`. Confirm which one nginx (or Apache) is using by checking the site config for the socket, for example `unix:/run/php/php8.4-fpm.sock`. The examples below use 8.4; substitute the version you find.

### PHP (do not edit the packaged php.ini)

Leave `/etc/php/8.4/fpm/php.ini` untouched so package upgrades do not prompt about a modified file. Drop an override into `conf.d` (it loads after `php.ini`):

```bash
sudo nano /etc/php/8.4/fpm/conf.d/99-uploads.ini
```

```ini
upload_max_filesize = 16M
post_max_size = 20M
max_execution_time = 120
```

`post_max_size` must be larger than `upload_max_filesize` (multipart overhead). The `99-` prefix loads last. Then:

```bash
sudo systemctl restart php8.4-fpm
```

If a pool file under `/etc/php/8.4/fpm/pool.d/` sets `php_value[upload_max_filesize]` or `php_admin_value[...]`, that value wins. Check with:

```bash
grep -n upload_max_filesize /etc/php/8.4/fpm/pool.d/*
```

### Nginx

Nginx’s default `client_max_body_size` is `1m`. In the site’s `server` block:

```nginx
client_max_body_size 16m;
```

Then `sudo nginx -t && sudo systemctl reload nginx`.

### Confirm

Create a temporary `phpinfo.php` in the Piwigo root, open it in a browser, and check `upload_max_filesize` and `post_max_size`. Delete the file after. `php --ini` shows the CLI config, not the FPM config the site uses.

## Privacy levels (optional override)

`--privacy-level` defaults to `everybody` (0). Higher user levels can see lower photo levels.

| Name | Number | Who can see the photo |
|------|--------|------------------------|
| everybody | 0 | Everyone who can open the album |
| contacts | 1 | Contacts and above |
| friends | 2 | Friends and above |
| family | 4 | Family and above |
| admins | 8 | Admins only |

```bash
python run.py --config piwigo-config.json --csv data.csv --privacy-level friends
```

## Sub-albums (optional)

The uploader does not create sub-albums unless you ask.

- `--parent-album "Name"` creates each Carton album under that parent.
- `--recursive` also applies the group permission to existing sub-albums. It does not affect sub-albums created later.

New sub-albums do not inherit group permissions. The advanced option `$conf['inheritance_by_default'] = true` (self-hosted) can change this for some paths; it is not the default.

## ShareAlbum (optional album link)

ShareAlbum shares a whole private album, not a collection. It is not needed for the curator workflow above. If you install it:

- Keep the album private. Public albums do not get a share link.
- Photos must be Everybody for the link to show them.
- By default only administrators create the link. Enable the non-admin power-user option only if a non-admin should share whole albums.
- Hide menus so the visitor does not browse other public albums.
- Regenerate or cancel to invalidate a link.
