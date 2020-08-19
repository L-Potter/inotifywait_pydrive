import subprocess
import os, sys
from argparse import ArgumentParser
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFileList
from stat import *

def auth():
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("credentials.json")
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
        #gauth.CommandLineAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        print("refreshing")
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile("credentials.json")

    drive = GoogleDrive(gauth)
    return drive

#event: MOVE_TO,CLOSE_WRITE,CLOSE
def upload_file(drive,filename,folder_id):
    f = drive.CreateFile({"title":filename,"parents": [{"kind": "drive#fileLink", "id": folder_id}]})
    if os.stat(filename).st_size > 0:
        f.SetContentFile(filename)
    f.Upload()
#event: MOVE_FROM,MOVE_FROM,ISDIR
def Trash(drive,target_id):
    """ 
        use ID to remove file or folder
    """
    folder = drive.CreateFile({'id': target_id})
    folder.Trash()
def get_folder_id(drive, parent_folder_id, folder_name):
    """ 
        Check if destination folder exists and return it's ID
    """
    # Auto-iterate through all files in the parent folder.
    file_list=GoogleDriveFileList()
    try:
        file_list = drive.ListFile({'q': "'{0}' in parents and trashed=false".format(parent_folder_id)}).GetList()
    # Exit if the parent folder doesn't exist
    except googleapiclient.errors.HttpError as err:
        # Parse error message
        message = ast.literal_eval(err.content)['error']['message']
        if message == 'File not found: ':
            print(message + folder_name)
            exit(1)
        # Exit with stacktrace in case of other error
        else:
            raise
    # Find the the destination folder in the parent folder's files
    for file1 in file_list:
        if file1['title'] == folder_name:
            print('title: %s, id: %s' % (file1['title'], file1['id']))
            return file1['id']
def get(drive,folder_name,parent_folder_id):
    '''
        get file or folder's ID
    '''
    folder_name_list = folder_name.split('/', -1 )
    if folder_name == '':
        return parent_folder_id
    if(len(folder_name_list) > 1):
        #print(f'user this tag find folder id {folder_name_list[0]}')
        #print(f'folder id:{parent_folder_id}')
        #下一層的資料夾的ID
        parent_folder_id_1 = get_folder_id(drive,parent_folder_id,folder_name_list[0])
        #print(f'parent_folder_id: {parent_folder_id_1}')
        numList = folder_name_list[1:]
        seperator = '/'
        result = seperator.join(numList)
        return get(drive,result,parent_folder_id_1)
    else:
        #print(f'user this tag find folder id {folder_name_list[0]}')
        parent_folder_id_end = get_folder_id(drive,parent_folder_id,folder_name_list[0])
        print(f'ID is :{parent_folder_id_end}')
        return parent_folder_id_end
def create_folder(drive, folder_name, parent_folder_id):
    """ 
        Create folder on Google Drive
    """
    folder_metadata = {
        'title': folder_name,
        # Define the file type as folder
        'mimeType': 'application/vnd.google-apps.folder',
        # ID of the parent folder        
        'parents': [{"kind": "drive#fileLink", "id": parent_folder_id}]
    }
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']
def upload_files_folder(drive,src_folder_name,parent_folder_id):
    """ 
        Upload files in the local folder to Google Drive 
    """
    # Enter the source folder
    try:
        os.chdir(src_folder_name) # $cd
    # Print error if source folder doesn't exist
    except OSError:
        print(src_folder_name + ' is missing')
    # Auto-iterate through all files in the folder.
    for file1 in os.listdir('.'): #list file in folder '.' 
        # Check the file's size
        statinfo = os.stat(file1)
        if S_ISDIR(statinfo.st_mode):
            result = create_folder(drive,file1,parent_folder_id)
            #print(result)
            upload_files_folder(drive,file1,result)
        elif statinfo.st_size > 0: 
            print('uploading ' + file1)
            # Upload file to folder.
            f = drive.CreateFile(
                {"parents": [{"kind": "drive#fileLink", "id": parent_folder_id}]})
            f.SetContentFile(file1)
            f.Upload()
        # Skip the file if it's empty
        else:
            print('file {0} is empty'.format(file1))
    os.chdir('..') 

def upload(drive,filename,target_id):
    folder = drive.CreateFile({'id': target_id})
    folder.SetContentFile(filename)
    folder.Upload()

def go_back(path):
    # Enter the source folder
    _path = path.split('/', -1 )
    for i in range(len(_path)):
        os.chdir('..')
    
def go_to(path):
    try:
        os.chdir(path) # $cd
    # Print error if source folder doesn't exist
    except OSError:
        print(path + ' is missing')
    # Auto-iterate through all files in the folder.

def main():
    parser = ArgumentParser()
    #parser.add_argument("n", help="repeat time", type=int)
    parser.add_argument("-name", "--filename", dest="fileName",type=str,required=True)
    parser.add_argument("-event", "--event", dest="event",type=str,required=True)
    parser.add_argument("-path", "--directory", dest="directory",type=str,required=True)

    args = parser.parse_args()

    drive = auth()
    #case 1 .create,ISDIR
    if args.event=="CREATE,ISDIR":
        if args.directory=="root":
            create_folder(drive,args.fileName,'root')
        else:
            parent_folder_id = get(drive,args.directory,"root")
            create_folder(drive,args.fileName,parent_folder_id)
            
    elif args.event=="CLOSE_WRITE,CLOSE" or args.event=="MOVED_TO":
        if args.directory=="root":
            isExist = get(drive,args.fileName,"root")
            if isExist is not None:
                upload(drive,args.fileName,isExist)
                return
            upload_file(drive,args.fileName,'root')
        else:
            url = args.directory+"/"+args.fileName
            isExist = get(drive,url,"root")
            if isExist is not None:
                go_to(args.directory)
                upload(drive,args.fileName,isExist)
                go_back(args.directory)
            elif isExist is None:
                go_to(args.directory)
                print("hello")
                parent_folder_id = get(drive,args.directory,"root")
                upload_file(drive,args.fileName,parent_folder_id)
                go_back(args.directory)

    elif args.event=="DELETE,ISDIR" or args.event=="MOVED_FROM,ISDIR":
        url = args.directory+"/"+args.fileName
        target_id = get(drive,url,"root")
        Trash(drive,target_id)

    elif args.event=="MOVED_FROM" or args.event=="DELETE":
        url = args.directory+"/"+args.fileName
        target_id = get(drive,url,"root")
        Trash(drive,target_id)

    elif args.event=="MOVED_TO,ISDIR":
        if args.directory=="root":
            folder_id = create_folder(drive,args.fileName,'root')
            upload_files_folder(drive,args.fileName, folder_id)
        else:
            parent_folder_id = get(drive,args.directory,"root")
            folder_id = create_folder(drive,args.fileName,parent_folder_id)
            go_to(args.directory)
            upload_files_folder(drive,args.fileName, folder_id)
            go_back(args.directory)

if __name__ == "__main__":
    main()
