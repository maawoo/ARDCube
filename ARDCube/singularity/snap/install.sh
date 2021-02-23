#!/bin/bash

#SNAPVER=8

# Install and update snap (Toolbox selection in response.varfile!)
#wget -q -O /src/snap/esa-snap_sentinel_unix_${SNAPVER}_0.sh \
#    "https://step.esa.int/downloads/${SNAPVER}.0/installers/esa-snap_sentinel_unix_${SNAPVER}_0.sh"
#sh /src/snap/esa-snap_sentinel_unix_${SNAPVER}_0.sh -q -varfile /src/snap/response.varfile
sh src/snap/esa-snap_sentinel_unix_8_0.sh -q -varfile /src/snap/response.varfile

# Current workaround for "commands hang after they are actually executed":  
# https://senbox.atlassian.net/wiki/spaces/SNAP/pages/30539785/Update+SNAP+from+the+command+line
/usr/local/snap/bin/snap --nosplash --nogui --modules --update-all 2>&1 | while read -r line; do
    echo "$line"
    [ "$line" = "updates=0" ] && sleep 2 && pkill -TERM -f "snap/jre/bin/java"
done

# Set usable memory to 12G
echo "-Xmx12G" > /usr/local/snap/bin/gpt.vmoptions
