#!/bin/bash
# stop on errors
set -e

backup_dir=/backups
local_dir=/local_backups

local=0
prefix=backup

while [ "$1" != "" ]; do
    case $1 in
        -f | --file )           shift
                                filename=$1
                                ;;
        -l | --local )          local=1
                                ;;
        -h | --help )           usage
                                exit
                                ;;
        -p | --prefix )         shift
                                prefix=$1
                                ;;
        * )                     usage
                                exit 1
    esac
    shift
done

filename=${prefix}_$(date +'%Y_%m_%dT%H_%M_%S').sql
if [ ${local} == 0 ]
then
    dir=/backups
else
    dir=/local_backups
fi
FILENAME=${dir}/${filename}

# we might run into trouble when using the default `postgres` user, e.g. when dropping the postgres
# database in restore.sh. Check that something else is used here
if [ "$POSTGRES_USER" == "postgres" ]
then
    echo "creating a backup as the postgres user is not supported, make sure to set the POSTGRES_USER environment variable"
    exit 1
fi

# Set the default database to be the username
: ${POSTGRES_DB:=$POSTGRES_USER}
export POSTGRES_DB

# export the postgres password so that subsequent commands don't ask for it
export PGPASSWORD=$POSTGRES_PASSWORD

echo "creating backup"
echo "---------------"

echo "Full backup filename ${FILENAME}"

pg_dump -h postgres -U $POSTGRES_USER $POSTGRES_DB >> $FILENAME

echo "successfully created backup $FILENAME"
echo $FILENAME

