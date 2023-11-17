#!/bin/bash
 
 #script for converting VETSA 2 raw DICOMS to BIDS format

 
 # Activate dcm2bids environment 
#conda activate dcm2bids

for vetsaid in `cat sublist_v2.txt`
do
	echo "Starting conversion of ${vetsaid}..."

	#run dcm2bids.
	dcm2bids -d ~/netshare/SYNVETSACOPY/data/vetsa/VETSA2/orig/${vetsaid}_v2/ -p ${vetsaid} -s ses-02 -c ~/netshare/M/MRI/BIDS/code/dcm2bids_config_v2.json -o ~/netshare/M/MRI/BIDS/data/
	
	echo "Finished converting ${vetsaid}."
done


	
	
