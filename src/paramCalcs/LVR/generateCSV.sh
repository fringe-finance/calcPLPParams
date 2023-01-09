#!/bin/bash

cd $1
urlFile="OHLCUrls.txt"
headingRow='Open time,Open,High,Low,Close,Volume,Close time,Quote asset volume,Number of trades,Taker buy base asset volume,Taker buy quote asset volume,Ignore'

apiUrls=$(cat $urlFile | sed 's/\s\+/\n/g')

for apiUrl in $apiUrls
do
    rm -rf ./work;
    mkdir work;
    cd work; 
    wget -qO- $apiUrl --header='Connection: keep-alive'   --header='Accept: */*'   --header='User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Safari/537.36'   --header='Sec-GPC: 1'   --header='Origin: https://data.binance.vision'   --header='Sec-Fetch-Site: cross-site'   --header='Sec-Fetch-Mode: cors'   --header='Sec-Fetch-Dest: empty'   --header='Referer: https://data.binance.vision/'   --header='Accept-Language: en-GB,en-US;q=0.9,en;q=0.8'   --compression=gzip | sed -E -e 's/data\/spot\/monthly\/klines\//https\:\/\/data.binance.vision\/data\/spot\/monthly\/klines\//g' | grep -Eo "(http|https)://[a-zA-Z0-9./?=_%:-]*" | sort -u | grep -wv CHECKSUM | grep .zip > zipUrls.txt
    wget -i zipUrls.txt
    rm ./zipUrls.txt
    unzip '*.zip'; 
    rm *.zip || { echo 'rm *.zip failed' ; exit 1; }
    cat *-*-*-*.csv > `ls *-*-*-*.csv | head -n 1`1; 
    rm ./*-*-*-*.csv; 
    mv `ls | head -n 1`  `ls | head -n 1`FINALFINAL.csv;
    sed -i "1i $headingRow" `ls`
    mv ./*FINALFINAL.csv ./../; 
    cd ..;
    rm -rf ./work;
done