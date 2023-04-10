# p4d-backup-restore
Perforce FlashArray snapshot backup and restore

This code used py-pure-client, follow the instrctions at https://github.com/PureStorage-OpenConnect/py-pure-client to install it on the perforce server. 

Prerequsite is that FlashArray is configured for Snap-to-NFS, a protection group (eg. PG-p4db2) is created with the Perforce DB1 volume (a_29_p4db2_new) on FlashArray and an offline target is enabled. Populate the 'config.ini' file with environment specific details and update the p4d specific details in the last section of the script. 


