---
layout: post
title: "Creating notes for different project with orgmode in Emacs"
date: 2018-04-16
---
I'm always amazed when I watch people mastering emacs. They can do
everything so much faster and with less keystrokes. However, if you have
no experience with elisp like me, extending emacs to do what I want
seems like a daunting task.

As always, reading books and blogs about Emacs can help (ironic that I
am writing about this isn't it), but practice beats everything when it
comes to learing a new programming language. That's why, after doing 20
times the same operation, I decided to implement some shortcut in Elisp.

What I am trying to achieve
===========================

I am working in multiple projects at a time, both in my professional and
personal life so I need to way to create notes quickly, and organize
them so that I can find them easily. I used to use Evernote for this but
after switching everything to Emacs I prefer using Orgmode.

My custom Emacs command will prompt me for a project and a note name,
and will create a file in the correctly directory that I can edit.

Let's dissect the problem a bit
===============================

Here I need a way to:

-   Find the list of my current projects
-   Get a name for the new note
-   Create the file name from above
-   Create the note and switch to orgmode

How to test Elips easily
------------------------

Elisp is much easier when you can test commands one by one. There is a
good tutorial [here](https://learnxinyminutes.com/docs/elisp/) on
lisp-interaction-mode. This tutorial also links the great essay by
Norvig about how to learn a programming language so I thought it was
appropriate to link it [here](http://norvig.com/21-days.html) as well.

Find all the projects
---------------------

Projects here are represented as subdirectory of the projects folder.
Basically, the folders are structured as: \~/notes/projects/, so notes
for project 'example' would be stored under \~/notes/projects/example/.

Here comes the first function. It will fetch all the directories under
the projects folder and ask the user to choose one.

```cl

(defvar my/project-path "~/notes/projects")

(defun my/pick-project ()
  "Prompt user to pick a choice from a list."
  (let ((choices (directory-files my/project-path)))
    (message "%s" (completing-read "Open bookmark:" choices ))))

```

Here, *directory-files* will list all the files in the given directory
(one improvement would be to keep only folders). Next line will prompt
me for a choice in this list of file and will return my choice.

Get a note name
---------------

To read a string from an user, read-string is the way to go.

```cl

(defun my/choose-note-name ()
  "Prompt user to choose a note name"
  (read-string "Choose the note name: "))

```

This will open a mini-buffer and will display "Choose the note name: ".
It will return the user's answer.

Concatenate everything to get the note path
-------------------------------------------

I played around a bit with clojure so I was expecting concatenating a
list of strings to be as easy, but unfortunatly it is slightly more
complicated here. I am using the concatenate function that requires a
type specifier.

```cl
(concatenate 'string "string1" "string2")
```

In the next function, I am also using the let form which let (:')) me
write cleaner code.

```cl

(defun my/create-note-name ()
  (let ((project-name (my/pick-project))
    (note-name (my/choose-note-name)))
    (concatenate 'string
         me/project-path
         "/"
         project-name
         "/"
         note-name
         ".org")))

```

The hardcoded slashes are ugly and I pretty sure there is a better way
to create the path from tokens...

Create the note
---------------

You can use find-file to create a file and edit it in the current
window. In my case, I want to open a new window to edit the note so I am
using find-file-other-window instead.

The function looks like:

```cl

(defun my/create-new-project-note ()
  (interactive)
  (let ((filename (my/create-note-name)))
    (find-file-other-window filename)
    (org-mode)))

```

Notice (interactive) which is there to make the function available when
typing M-x. (org-mode) is also called after switching buffer so that the
correct mode is used for editing the note.

It's done! But...
=================

There is a lot of things to improve:

-   I'd like to be able to create a new project if it does not exist
    instead of having to create a new folder myself.
-   directory-files lists all files in a directory, including
    non-folders and ".", "..". These need to be filtered out.
-   Concatenating is ugly.
-   After creating a note, I am using yasnippet to set the note
    skeleton. There should be a way to automize that.

That first experience with Elisp was anyway encouraging as I used this
function everyday. Stay tuned for other code dissection ;)

Full code
=========

```cl

(defvar my/project-path "~/Nextcloud/notes/projects")

(defun my/pick-project ()
  "Prompt user to pick a choice from a list."
  (let ((choices (directory-files my/project-path)))
    (message "%s" (completing-read "Open bookmark:" choices ))))

(defun my/choose-note-name ()
  "Prompt user to choose a note name"
  (read-string "Choose the note name: "))


(defun my/create-note-name ()
  (let ((project-name (my/pick-project))
    (note-name (my/choose-note-name)))
    (concatenate 'string
         me/project-path
         "/"
         project-name
         "/"
         note-name
         ".org")))

(defun my/create-new-project-note ()
  (interactive)
  (let ((filename (my/create-note-name)))
    (find-file-other-window filename)
    (org-mode)))

```
