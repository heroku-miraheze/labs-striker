#!/usr/bin/env bash
# Ugly collectstatic command to keep django-autocomplete-light from making
# a mess of the staticfiles directory.
#
# Django's collect static maintenance script has an --ignore option, but
# strangely the way that it is implemented inside the script you can only
# exclude based on the name of a single directory or file. Ideally you would be
# able to exclude a more descriptive path such as
# django-autocomplete-light/vendor/vendor
#
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
$DIR/manage.sh collectstatic -c --noinput \
    --ignore src \
    --ignore tests \
    --ignore *.json \
    --ignore Gruntfile.js
cd $DIR/../staticfiles
python -mjson.tool staticfiles.json > staticfiles.json.pretty
mv staticfiles.json.pretty staticfiles.json
