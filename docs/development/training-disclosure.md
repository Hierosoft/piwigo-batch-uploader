# Training Disclosure for piwigo-batch-uploader
This Training Disclosure, which may be more specifically titled above here (and in this document possibly referred to as "this disclosure"), is based on **Training Disclosure version 1.1.4** at https://github.com/Hierosoft/training-disclosure by Jake Gustafson. Jake Gustafson is probably *not* an author of the project unless listed as a project author, nor necessarily the disclosure editor(s) of this copy of the disclosure unless this copy is the original which among other places I, Jake Gustafson, state IANAL. The original disclosure is released under the [CC0](https://creativecommons.org/public-domain/cc0/) license, but regarding any text that differs from the original:

This disclosure also functions as a claim of copyright to the scope described in the paragraph below since potentially in some jurisdictions output not of direct human origin, by certain means of generation at least, may not be copyrightable (again, IANAL):

Various author(s) may make claims of authorship to content in the project not mentioned in this disclosure, which this disclosure by way of omission unless stated elsewhere implies is of direct human origin unless stated elsewhere. Such statements elsewhere are present and complete if applicable to the best of the disclosure editor(s) ability. Additionally, the project author(s) hereby claim copyright and claim direct human origin to any and all content in the subsections of this disclosure itself, where scope is defined to the best of the ability of the disclosure editor(s), including the subsection names themselves, unless where stated, and unless implied such as by context, being copyrighted or trademarked elsewhere, or other means of statement or implication according to law in applicable jurisdiction(s).

Disclosure editor(s): Hierosoft LLC

Project author: Hierosoft LLC

This disclosure is a voluntary of how and where content in or used by this project was produced by LLM(s) or any tools that are "trained" in any way.

The main section of this disclosure lists such tools. For each, the version, install location, and a scope of their training sources in a way that is specific as possible.

Subsections of this disclosure contain prompts used to generate content, in a way that is complete to the best ability of the disclosure editor(s).

tool(s) used:
- Grok

Scope of use: code described in subsections--typically modified by hand to improve logic, variable naming, integration, etc, but in this commit, unmodified.


# *.py, *.sh, *.toml
- 2026-08-24
  - https://grok.com/c/3e24df6b-5fd0-400e-aaeb-66e0ea273ae7?rid=776c6819-4518-489f-900f-9db2b54678b7

Is there any self-hosted open source multi-user gallery (similar to deviantart)? I would maybe consider pleroma, but I don't want to have a complex system that fights what I want to do. I also want a way to make my gallery private, and only visible to friends. Hopefully shareable via a sharing link (or a system where I can write a plugin to generate a sharing link). I want to somewhat naturally write a mass upload script/plugin that can take images from a database and post them one by one (not all at once--I need to put both spreadsheet data and an image together to make a post). There needs to be some way for another user to like items or add them to a list/favorites easily, and to comment.

Make a batch uploader in Python. The api_key_id and api_key will be in a json file. A CSV file will be used for the batch import and will have the following columns: Description Date # Code Location Carton Comment Frame,Brand Scanned,File,Date Film,Reel,Serial,Path. Use Description field for title. Upload the image file itself as well (from Path). Use an album named by the "Carton" column's value (create the album if it doesn't exist); described by the "Location" column's value as "Location: Metal box". For the photo's description include any columns left over, separate lines if possible, such as "Date: Jan '00\nComment:in plastic frame" and other remaining info that is not blank.

Show "Path: " in the composite description as well. I want each album to be shared with a friends group.

If the Description field of the source csv contains "(portrait" (case insensitive) rotate left, except if the Description contains "rotate right", then rotate right. Use a temporary copy of the file so the original is not edited.

If the description contains "rotate 180" rotate 180 degrees.

Split it into a main file, init file with global functions, and a piwigoclient.py file, all in morepiwigo module, and make a run.py to run main.

- 2026-11-14

Place the entire project in a new folder called piwigo-batch-uploader that will function as the repo. Add https://raw.githubusercontent.com/github/gitignore/refs/heads/main/Python.gitignore. Rename piwigo_batch_uploader to piwigo-batch-uploader/morepiwigo/__init__.py and make a piwigo-batch-uploader/run.py to run the application. Make a pyproject.toml, author Jake Gustafson e-mail 7557867+poikilos@users.noreply.github.com repo github.com/Hierosoft/piwigo-batch-uploader. Make a dependencies.sh which installs python3-pillow or detects the presence of the yum or dnf command or other and installs the correct package name for the particular ecosystem (including if AlmaLinux differs in some cases--I know CentOS had certain package names that differed from Fedora). Add dependencies.txt as a fallback. Make sure any packages we depend on that have OS packaged versions that we install such packages in dependencies.sh.

I can't see the canvas. Fix its settings for this Grok project and/or provide a zip of the repo folder.

Make readme.md filename all lowercase.

Add these files to the repo folder.
- attach piwigo-batch-uploader.code-workspace, run.sh, and license.txt

Add a piwigo.md which explains, using simple example username(s) how to create a friends group, whether case matters for the purposes of the batch uploader, etc., and how to make a folder or subfolder (album or sub album?? whatever container type is apppropriate) accessible to the group (and whether we can do batch uploading to an album that is shared and have some sub-container added later automatically shared--if that is possible, adjust the program/instructions/tooltips/arg-help to allow that).

Explain the container(s) and structure of piwigo, with an emphasis on permissions. Explain how we use it now, and if it can be simplified by setting a group on upload, and not having sub-albums (preferred).

Ok, make sure we don't require --parent-album nor --recursive, nor create sub-albums by default. The piwigo.md should explain how to add friends, and how that is related to the command-line options. That should be explained concisely, and you can add a separate "Sub-albums (optional)" markdown heading to explain sub-albums.

Load the whole CSV into an in-memory OrderedDict of lists, where key is title row's value for the column, and where list item [0] is the first entry (idx 0 is 2nd row of file since 1st row as title row is required). If the CSV does not yet have an "Uploaded" column after that is prepared, add the "Uploaded" column and fill it with 0s. Each time an upload is successful, change the value to 1 for that entry (at idx). Only if at least one upload succeeds, save the CSV on error (in which case, stop processing additional rows) or completion (all rows processed without error). If there is a way to detect if an image was already uploaded, try that (show warning, but don't mark as uploaded, since I am not sure how accurate that will be yet. Explain how it will work if possible, otherwise skip it. If it is possible if we add a new column for some type of ID that we get back on upload if we get anything back, do that).

Whenever saving a file, write to a tmp file first, and only if completes successfully: remove the real file if exists (but rename it to .bak if no .bak exists yet, instead of deleting) and rename the tmp file to the real filename. You don't have to keep zipping every prompt anymore--I found the file tree in the canvas using the "Show files" symbol button.

If there are only preset sharing levels, not groups per se, on Piwigo, should we rename --friends-group to --share-with?

can we set --privacy-level as an additiona option (Is that in the upload API)?

Require the privacy level option to be set. Make the primary setup in piwigo.md explain how to add someone as a friend, and describe the relationship with the --privacy-level option. Rename --friends-group arg to --share-with-group and make sure it is not required. Cover --share-with-group in a new section (adapt the old content to the new section, but be concise and assume knowledge of the refined main section). To avoid confusion do not use a group name of "Friends" in the group tutorial, since that is ambiguous with the privacy level.

I have the following columns in my csv: 
Favorite	Description	Date	#	Code	Location	Carton	Comment	Frame Brand	Scanned File Date	Film Reel Serial	Path. Why do I get the following error?
```
[1/181] bowl
  ERROR: Expecting value: line 1 column 1 (char 0)

Stopped on error. Success: 0, Errors: 1
```
The first row is: 
FALSE	bowl	July '93		N09	Metal Box (black)?	red paper carton - "Color Slides" carton (Apr '90 - Feb '00)			2026-08-06		2026-08-07/IMAG0003.JPG

Add a blank line, then piwigo-batch-uploader then --------------------- at the start of the program for deliniating the output.
The ws.php query you provided results in `{"stat":"ok","result":{"username":"guest","status":"guest","theme":"modus","language":"en_US","pwg_token":"c3cd285a3596de28136267231467d524","charset":"utf-8","current_datetime":"2026-11-15 15:56:15","version":"16.4.0","save_visits":true,"connected_with":null,"available_sizes":["square","thumb","2small","xsmall","small","medium","large","xlarge","xxlarge"]}}`
The result of running the new code is:
```
Found 181 rows

[1/181] bowl
  ERROR: Piwigo did not return JSON for pwg.categories.getList (HTTP 200 from https://example.com/ws.php). Response starts with: <?xml version="1.0" encoding="utf-8" ?>
<rsp stat="ok">
<categories />
</rsp>
```

Now we get:
```
[1/181] bowl
  Creating album: 'red paper carton - "Color Slides" carton (Apr \'90 - Feb \'00)'  (Location: Metal Box (black)?)
  ERROR: 401 Client Error: Access denied for url: https://example.com/ws.php?format=json

Stopped on error. Success: 0, Errors: 1
```
Even though I have the base_url (which works for your ws status check), API id and key in piwigo-config.json.

I am not able to get to admin settings. admin.php says I am not authorized. However, I am using the only admin user I know I set up. How can we fix it, such as at the db level?

Ok, I do have a user named admin, and I found the password in my list. Why would uploader user need to be admin to create albums? I though this was a multi-tennant site. Is it just one gallery?

I promoted the uploader user to Admin. Can any user make a public sharing link to a private album? I want a third user to be able to comment on photos, edit the titles or at least add comments, and share the photos. Worst case: I will go on as admin and make individual photos public. Let me know the cooperative curating plan and ask clarifying questions before implementing. Assume 16.5.0. I will do the upgrade.

I am willing to use a plugin, but explain the one-time link concept in ShareAlbum. I want a permanent link (accessible to anyone, even if not logged in) if possible, even if the link is obfuscated (long).

Explain the minimal ShareAlbum setup in piwigo.md. If there are options necessary to accomplish my goal, mention them. If there are other options you've discussed or not discussed, add a new sub-section for that.

The plugin description says,
```
Plugin to enable simple sharing of private albums.
For any private album, you can generate a unique URL that you can share with the users you trust in enough to browse an album. No user nor password is required by default for visitors of this trusted link.

The plugin will allow you to share entire albums (where individual pictures visibility is 'everybody'. Pictures with restricted visibility to admin only, family, contacts specific, will not be displayed through the shared link)
```
. Is there any way to prevent visitors (not logged in) from viewing photos without the URL?

In that case, make those the defaults for the uploader and do not require privacy-level.

Does the third user have to be part of sharealbum_powerusers or sharealbum? Ideally I want them to be able to share an individual photo publicly, but not an album.

Why does Private Share have a rating of 1.75 on their plugins list? It is hosted on the official Piwigo account on GitHub.

How does the link work with UserCollections? How does a user use UserCollections?

Explain the filter system in the plugin's settings.

I want the uploader user and the curator to be friends--I assume that is necessary and makes it possible for the curator to see all photos the uploader uploads (that is the first requirement). The new requirement is that I want the curator user to be able to make any collection(s) and make any of those public (no login required to view).

If we really need the group (not just privacy level set to friends), add it by default but name it "curators". If not, clarify what you mean by "Without this the curator sees nothing". Update piwigo.md main section to focus entirely on achieving my stated requirements (with the clarification that the non-admin curator will share a collection not an individual photo with a permanent public link), including creating the group if necessary. Remember we also need the curator to be able to rename photos or at least comment on them (comments should be publicly visible--if we need any privacy level on the user to accomplish that, explain that as well--I don't want to show the users' e-mail addresses publicly though). Do I need to check "Activate Comments" in settings? Ideally I only want admin/curators to comment (any users given the ability to view a given photo/collection including public may be allowed if necessary to accomplish that). Ideally I want public (not logged in users) to only view the photos in the collections shared with sharing links.

In piwigi.md, explain how the uploader user can be added as admin as necessary to create albums, and how the uploader can log in and add the curator as a friend, and whether the curator must accept the request somehow.

Maintain and refer to piwigo-config.example.json instead of putting a json block directly in the readme.

If the image is not found, and the path is not absolute, prepend the folder containing the CSV to the image path.

```
redacted@redacted:/media/redacted/SD16/DCIM$ bash upload-100MEDIA.sh
Checking paths...
Checking for csv...
Syncing...
sending incremental file list

sent 5,735 bytes  received 20 bytes  11,510.00 bytes/sec
total size is 668,394,388  speedup is 116,141.51

piwigo-batch-uploader
---------------------
Authenticated as 'uploader' (status=admin)
Found 181 rows

[1/181] bowl
  Path relative to CSV: /media/redacted/SD16/DCIM/100MEDIA/2026-08-07/IMAG0003.JPG
Using group 'curators' (id=3)
  ERROR: 413 Client Error: Request Entity Too Large for url: https://example.com/ws.php?format=json

Stopped on error. Success: 0, Errors: 1
```

Is there anywhere else, like /etc/local or somewhere in /etc/php with conf.d, where we can override /etc/php/8.4/fpm/php.ini while leaving the packaged php.ini intact to avoid debian upgrade warnings (replace with maintainer's copy)?

Assume a max image size of 12 MB. Document the settings in piwigo.md. Use 8.4 as an example, but instruct on how to find the current running version(s) of the fpm service.

why are you using a capital "M" in "1M" when both the nginx and angie documentation say lowercase? Is either ok?

Add a manual upload section to the piwigo.md and explain how an uploader user can use the web interface to create an album and upload image(s) with all of the proper permissions/steps to allow the curator user to browse them, place them in collections, and share them.

What is the point of a watermark if people can just click "original"? Will that feature at least be hidden from public collections or what?

Ok, there seems to be no problem after all. If I log out then go to a shared collection link, I can click on a photo to go to the popout, but clicking "jump to photo" which would normally show the photo editing interface and size drop down (available even without the Download by Size plugin, so I'm not sure the point of that plugin), instead shows a login screen. They can't even get to the screen with the Download This File option, so we don't have to start removing widgets. I don't see any High definition option in the guest user editor (See attached screenshots. If I click permissions, it only shows which albums they can access, nothing else). 
