#!/bin/bash

####
# Based on https://github.com/mundialis/esa-snap/blob/ubuntu/snap/install.sh
####

# https://senbox.atlassian.net/wiki/spaces/SNAP/pages/30539778/Install+SNAP+on+the+command+line
# https://senbox.atlassian.net/wiki/spaces/SNAP/pages/30539785/Update+SNAP+from+the+command+line
# http://step.esa.int/main/download/snap-download/

SNAPVER=8

# avoid NullPointer crash during S-1 processing
java_max_mem=10G

# set JAVA_HOME (done in Docker as well)
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# install module 'jpy' (A bi-directional Python-Java bridge)
git clone https://github.com/bcdev/jpy.git /src/snap/jpy
pip3 install --upgrade pip wheel
(cd /src/snap/jpy && python3 setup.py bdist_wheel)
# hack because ./snappy-conf will create this dir but also needs *.whl files...
mkdir -p /root/.snap/snap-python/snappy
cp /src/snap/jpy/dist/*.whl "/root/.snap/snap-python/snappy"

# install and update snap (s1tbx toolbox only)
wget -q -O /src/snap/esa-snap_sentinel_unix_${SNAPVER}_0.sh \
    "https://step.esa.int/downloads/${SNAPVER}.0/installers/esa-snap_sentinel_unix_${SNAPVER}_0.sh"
sh /src/snap/esa-snap_sentinel_unix_${SNAPVER}_0.sh -q -varfile /src/snap/response.varfile

# Current workaround for "commands hang after they are actually executed":  https://senbox.atlassian.net/wiki/spaces/SNAP/pages/30539785/Update+SNAP+from+the+command+line
# /usr/local/snap/bin/snap --nosplash --nogui --modules --update-all
/usr/local/snap/bin/snap --nosplash --nogui --modules --update-all 2>&1 | while read -r line; do
    echo "$line"
    [ "$line" = "updates=0" ] && sleep 2 && pkill -TERM -f "snap/jre/bin/java"
done

# create snappy and python binding with snappy
/usr/local/snap/bin/snappy-conf /usr/bin/python3
(cd /root/.snap/snap-python/snappy && python3 setup.py install)

# increase the JAVA VM size to avoid NullPointer exception in Snappy during S-1 processing
(cd /root/.snap/snap-python/snappy && sed -i "s/^java_max_mem:.*/java_max_mem: $java_max_mem/" snappy.ini)

# get minor python version
PYMINOR=$(python3 -c 'import platform; major, minor, patch = platform.python_version_tuple(); print(minor)')
(cd /usr/local/lib/python3.$PYMINOR/dist-packages/snappy/ && sed -i "s/^java_max_mem:.*/java_max_mem: $java_max_mem/" snappy.ini)

# test
/usr/bin/python3 -c 'from snappy import ProductIO'

# cleanup installer
rm -f /src/snap/esa-snap_sentinel_unix_${SNAPVER}_0.sh

################################################################################
# keep for debugging
# export INSTALL4J_KEEP_TEMP=yes