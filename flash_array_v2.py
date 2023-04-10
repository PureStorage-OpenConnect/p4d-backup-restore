import urllib3
from purestorage import FlashArray
import argparse
import configparser
import os
import time, sys

urllib3.disable_warnings()


def listvolume(volume):
    print('Vol name:', volume)
    for v in array.list_volumes():
        if v['name'].startswith(volume):
            print(v)


def createsnapshot(pgname,replicate=False):
    # handle create snapshot 
    print('PG name:', pgname)
        
        # include perforce quecise command here
        # rotate journal here or after this 

    if replicate:
        print('\nCreating protection group snapshot and replicating to offload target')
        array.create_pgroup_snapshot(pgname, replicate_now=True)
    else:
        print('\nCreating protection group snapshot')
        array.create_pgroup_snapshot(pgname, replicate_now=False)


def listsnapshots(volume,target=False):
    
    
    if target:
        snaps = array.list_volumes(snap=True, on=offloadtarget)
        
        latestsnapremote=snaps[len(snaps)-1]['name']
        config.set('p4', 'remotesourcesnap',latestsnapremote)

        print('\nAvailable snapshot for Volume : ', volume, 'on offload target', offloadtarget)
        for v in snaps:
            #print(type(v['source']))
            volname = array_info['array_name'] + ":" + volume
            if v['source'].startswith(volname):
                print(v['name'])
        #get the latest snapshot and use it for restore
    else:
        snaps = array.list_volumes(snap=True)

        latestsnap=snaps[len(snaps)-1]['name']
        config.set('p4', 'sourcesnap',latestsnap)
        print('\nAvailable local snapshot for Volume : ', volume)
        for v in snaps:
            if v['source'].startswith(volume):
                print(v['name'])
        #get the latest snapshot and use it for restore
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def clonevol(sourcesnap):
    targetvolume=config['p4']['targetvolume']
    overwrite=config['p4']['overwrite']
    print("\nCopying {} to {}, with overwrite {}".format(sourcesnap, targetvolume, overwrite))
    if overwrite:
        print("\nOverwriting the volume from latest local snapshot")
        array.copy_volume(sourcesnap, targetvolume, overwrite=overwrite)
        
    else:
        print("\nCreating a new volume from latest local snapshot")
        targetvolume = targetvolume + "-new"
        array.copy_volume(sourcesnap, targetvolume)

def restoresnap(snap):
    
    print("\nRestoring {} from offload target - {}, snap=True".format(remotesourcesnap, offloadtarget))
    array.create_snapshot(remotesourcesnap, snap=True, on=offloadtarget)



def runoscommand(cmd):
     print('Executing {}'.format(cmd))
     os.system(cmd)





if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)

    subparser = parser.add_subparsers(dest='command')

    #Main options

    createsnap = subparser.add_parser('createsnap')
    listsnap = subparser.add_parser('listsnap')
    restorevol = subparser.add_parser('restorevol')
    #restorevol.add_argument('--sourcesnap', help="Source snapshot", type=str)
    restoresnap = subparser.add_parser('restoresnap')
    applyjournal = subparser.add_parser('applyjournal')

    config = configparser.ConfigParser()
    config.read('config.ini')

    flasharrayip=config['p4']['flasharrayip']
    user=config['p4']['user']
    password=config['p4']['password']
    
    volumename=config['p4']['volumename']
    targetvolume=config['p4']['targetvolume']
    pgname=config['p4']['pgname']
    offloadtarget=config['p4']['offloadtarget']
    overwrite=config['p4']['overwrite']
    db1fs=config['p4']['db1fs']
    

    array = FlashArray(flasharrayip,user,password)
    array_info = array.get()
    print("Connected to FlashArray {} ".format(array_info['array_name']))

    try:
        options = parser.parse_args()
    except Exception as e:
        parser.print_help()
        sys.exit(1)
    
    
    if options.command == 'createsnap':
        #snapshot
        #step 1
        print('\nRotate journal')
        runoscommand('source /p4/common/bin/p4_vars 5;/p4/common/bin/rotate_journal.sh 5')
        print("\nsleep for 5 seconds.")
        time.sleep(5)
    
        #step 2
        print('\nTake protection group snapshot')
        createsnapshot(pgname,replicate=True)

        time.sleep(10)

        listsnapshots(volumename,target=True)
        print('\n---------------------------\n')
        listsnapshots(volumename)


    
    if options.command == 'listsnap':

        listsnapshots(volumename,target=True)
        print('\n\n---------------------------\n')
        listsnapshots(volumename)
    
    if options.command == 'restoresnap':
        print('\nRestoring lastest snapshot from offload target to local FlashArray. Make sure same snapshot does not exits on the array')
        inp = input('\nProceed Y/N ?')
        if inp == 'Y':            
            remotesourcesnap=config.get('p4', 'remotesourcesnap')
            print('\nRestoring from snapshot : ', remotesourcesnap)
            restoresnap(remotesourcesnap)
        elif inp == 'N':
            inpsnap = input('Provide the remote snap to restore ')
            print('\nRestoring from snapshot : ', inpsnap)
            restoresnap(inpsnap)

    if options.command == 'restorevol':
        
        #step 1

        inp = input('\nStopping p4d. Proceed Y/N ?')
        if inp == 'Y':  
            runoscommand('sudo systemctl stop p4d_5')
            time.sleep(1)
        elif inp == 'N':
            exit()
        
        #step 2
        inp = input('\nUnmounting  p4db1 mount. Proceed Y/N ?')
        if inp == 'Y':  
            runoscommand('sudo umount /p4db1_new')
            time.sleep(1)
        elif inp == 'N':
            exit()
        
        print('\nVerify  p4db1 mount')
        runoscommand('sudo df -h /p4db1_new')
        #time.sleep(1)
        # #step 3
        print('\nRestoring db1 volume from latest db2 snapshot on FlashArray.')
        inp = input('Proceed Y/N ?')
        if inp == 'Y':
            sourcesnap=config.get('p4', 'sourcesnap')        
            clonevol(sourcesnap)
            print('\nRestoring from latest snapshot : ', sourcesnap)
        elif inp == 'N':
            inpsnap = input('Provide the snap to use ')

            clonevol(inpsnap)
            print('\nRestoring from snapshot :', inpsnap)
        time.sleep(2)
        print('\nRescan Iscsi  and multipath')
        runoscommand('sudo iscsiadm -m session -sid 5 --rescan')
        runoscommand('sudo multipath')
        print('\nMounting db1 filesystem')
        runoscommand('sudo mount /p4db1_new')
        print('Updating p4db settings')
        runoscommand('mv /p4db1_new/p4/5/db2 /p4db1_new/p4/5/db1')
        runoscommand('ln -s /p4/4/root/license /p4/5/root/license')
        runoscommand("echo 'master.5' >/p4/5/root/server.id")
        print('Starting p4d')
        runoscommand('sudo systemctl start p4d_5')
        time.sleep(2)
        runoscommand('sudo systemctl status p4d_5')

    if options.command == 'applyjournal':
        print("Applying the live journal...")
        runoscommand('source /p4/common/bin/p4_vars 5;p4d -r /p4/5/root -jrf /p4/5/logs/journal')

    