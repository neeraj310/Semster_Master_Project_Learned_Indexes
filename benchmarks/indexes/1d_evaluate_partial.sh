#!/bin/bash
# Copyright (c) 2021 Xiaozhe Yao et al.
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

evaluate() {
    local id=$1
    local distribution=$2
    local numberOfData=100000
    if [[ "$distribution" == "lognormal" ]] 
    then
        echo "c-generator for lognormal..."
        src/utilities/c-generator/lognormal."$numberOfData".run
        echo "$i/3: Evaluating $distribution with $numberOfData points"
        python3 examples/1d_evaluate.py data/1d_"$distribution"_$numberOfData.csv > "$distribution"_"$numberOfData"_$i.log
    else
        python3 src/utilities/1d_generator.py "$distribution" $numberOfData
        echo "$i/3: Evaluating $distribution with $numberOfData points"
        python3 examples/1d_evaluate.py data/1d_"$distribution"_$numberOfData.csv > "$distribution"_"$numberOfData"_$i.log
    fi
}

batch_evaluate() {
    local dist=$1
    for i in {1..3}
        do evaluate "$i" "$dist"
    done
}

for dist in "lognormal" "normal" "uniform"
do
    batch_evaluate "$dist" &
done
