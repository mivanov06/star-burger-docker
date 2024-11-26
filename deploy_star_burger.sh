#!/bin/bash

set -e

cd /opt/star-burger/

git pull
source venv/bin/activate

pip install -r requirements.txt

npm ci
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

systemctl restart star-burger.service
systemctl reload nginx.service
echo "reload nginx"

rollbar_token=$ROLLBAR_TOKEN
rollbar_env=$ROLLBAR_ENV
commit_hash=$(git rev-parse HEAD)

curl --request POST --url 'https://api.rollbar.com/api/1/deploy' \
     --header 'X-Rollbar-Access-Token: '$rollbar_token'' \
     --header 'accept: application/json' \
     --header 'content-type: application/json' \
     --data '
            {
              "environment": "'"$ROLLBAR_ENV"'",
              "revision": "'"$commit_hash"'",
              "rollbar_username": "mivanov06",
              "local_username": "mivanov06",
              "comment": "new deploy",
              "status": "succeeded"
            }
            '

echo "Deploy has successefully finished"
