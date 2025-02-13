import ast
import boto3
import logging
import os
import sys
import traceback

LOG_FILE_NAME = 'output.log'

# Change region to match with the default region that you setup when configuring your AWS CLI
REGION = 'us-east-1'

class S3Handler:
    """S3 handler."""

    def __init__(self):
        self.client = boto3.client('s3')

        logging.basicConfig(filename=LOG_FILE_NAME,
                            level=logging.DEBUG, filemode='w',
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        self.logger = logging.getLogger("S3Handler")

    def help(self):
        print("Supported Commands:")
        print("1. createdir <bucket_name>")
        print("2. upload <source_file_name> <bucket_name> [<dest_object_name>]")
        print("3. download <dest_object_name> <bucket_name> [<source_file_name>]")
        print("4. delete <dest_object_name> <bucket_name>")
        print("5. deletedir <bucket_name>")
        print("6. find <pattern> <bucket_name> -- e.g.: find txt bucket1 --")
        print("7. listdir [<bucket_name>]")
    
    def _error_messages(self, issue):
        error_message_dict = {}
        error_message_dict['operation_not_permitted'] = 'Not authorized to access resource.'
        error_message_dict['invalid_directory_name'] = 'Directory name is invalid.'
        error_message_dict['incorrect_parameter_number'] = 'Incorrect number of parameters provided'
        error_message_dict['not_implemented'] = 'Functionality not implemented yet!'
        error_message_dict['bucket_name_exists'] = 'Directory already exists.'
        error_message_dict['bucket_name_empty'] = 'Directory name cannot be empty.'
        error_message_dict['non_empty_bucket'] = 'Directory is not empty.'
        error_message_dict['missing_source_file'] = 'Source file cannot be found.'
        error_message_dict['non_existent_bucket'] = 'Directory does not exist.'
        error_message_dict['non_existent_object'] = 'Destination File does not exist.'
        error_message_dict['unknown_error'] = 'Something was not correct with the request. Try again.'

        if issue:
            return error_message_dict[issue]
        else:
            return error_message_dict['unknown_error']

    def _get_file_extension(self, file_name):
        if os.path.exists(file_name):
            return os.path.splitext(file_name)

    def _get(self, bucket_name):
        response = ''
        try:
            response = self.client.head_bucket(Bucket=bucket_name)
        except Exception as e:
            # print(e)
            # traceback.print_exc(file=sys.stdout)
            
            response_code = e.response['Error']['Code']
            if response_code == '404':
                return False
            elif response_code == '200':
                return True
            else:
                raise e
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True
        else:
            return False

    def createdir(self, bucket_name):
        if not bucket_name:
            return self._error_messages('bucket_name_empty')

        try:
            if self._get(bucket_name):
                return self._error_messages('bucket_name_exists')
            self.client.create_bucket(Bucket=bucket_name)
        except Exception as e:
            print(e)
            raise e

        # Success response
        operation_successful = ('Directory %s created.' % bucket_name)
        return operation_successful

    def listdir(self, bucket_name):
        #checking the validates checks for listdir is only directory does not exist
        # non_existed_bucket & check the bucket exist
        # If bucket_name is provided, check that bucket exits.
        # If bucket_name is empty then display the names of all the buckets
        # If bucket_name is provided then display the names of all objects in the bucket
        if bucket_name == '':
             buckets = self.client.list_buckets()
             return [bucket['Name'] for bucket in buckets['Buckets']] 
        try:
            if not self._get(bucket_name):
                return self._error_messages('non_existed_bucket')
            if bucket_name:
                objects = self.client.list_objects(Bucket=bucket_name)
                return [obj['Key'] for obj in objects.get('Contents', [])]
        except Exception as e:
            print(e)
            raise e
                     

    def upload(self, source_file_name, bucket_name, dest_object_name=''):
       
      
       
        # 1. Parameter Validation
        #    - source_file_name exits in current directory
        #    - bucket_name exists
        if not os.path.exists(source_file_name):
            return self._error_messages('missing_source_file')
        if not self._get(bucket_name):
            return self._error_messages('non_existent_bucket')
        if not dest_object_name:
                dest_object_name = source_file_name
        try:
             # 3. SDK call
             # - When uploading the source_file_name and add it to object's meta-data
                self.client.upload_file(source_file_name,bucket_name,dest_object_name, ExtraArgs= {'Metadata': {'file_name': source_file_name}})
                operation_successful = ('File %s uploaded to directory %s.' % (source_file_name, bucket_name))
                return operation_successful
        except Exception as e:
            print(e)
            raise e


    def download(self, dest_object_name, bucket_name, source_file_name=''):
        # If the current directory already contains a file with source_file_name then move it as a backup
        # with following format: <source_file_name.bak>
        
        # Parameter Validation
        # checking non_existent_bucket & non_exitenet_object
        
        # if source_file_name is not specified then use the dest_object_name as the source_file_name
        if not source_file_name:
            source_file_name = dest_object_name
        #SDK call
        if os.path.exists(source_file_name):
            os.rename(source_file_name, source_file_name + ".bak") 
        try: 
            if not self._get(bucket_name):
                return self._error_messages('non_existent_bucket')
            if not dest_object_name:
                return self._error_message('non_existenet_object')
            self.client.download_file(bucket_name, dest_object_name, source_file_name)
            operation_successful = ('File %s downloaded from directory %s.' % (dest_object_name, bucket_name))
            return operation_successful
        except Exception as e:
            print(e)
            raise e
            
        



    def delete(self, dest_object_name, bucket_name):
        
        # Validation check: checking non_exitence_object and non_exitence_bucket
        if not self._get(bucket_name):
            return self._error_messages('non_existent_bucket')
        if not dest_object_name:
            return self._error_message('non_existenet_object')
        objects = self.client.list_objects(Bucket=bucket_name)
        objects_key = [obj['Key'] for obj in objects.get('Contents', [])]
        try:
            
            if dest_object_name in objects_key:
                self.client.delete_object(Bucket=bucket_name, Key = dest_object_name)
                operation_successful = ('File %s deleted from directory %s.' % (dest_object_name, bucket_name))
                return operation_successful
        except Exception as e:
            print(e)
            raise e

    def deletedir(self, bucket_name):
        # Delete the bucket only if it is empty
        
        # Success response
        # operation_successful = ("Directory %s deleted." % bucket_name)
        
        # Validation check: checking non_exitence_bucket and non_empty_bucket
        if not self._get(bucket_name):
                return self._error_messages('non_existent_bucket')
        if not self.client.list_objects(Bucket = bucket_name):
                return self._error_messages('non_empty_bucket')    
        try:
            self.client.delete_bucket(Bucket= bucket_name)
            operation_successful = ("Directory %s deleted." % bucket_name)
            return operation_successful
        except Exception as e:
            print(e)
            raise e


    def find(self, pattern, bucket_name=''):
        # Return object names that match the given pattern
        
        # Validation check : check for non_exitence_bucket
        if not self._get(bucket_name):
            return self._error_messages('non_existent_bucket')
        try:
            if bucket_name:
                objects = self.client.list_objects_v2(Bucket=bucket_name)
                return [obj['Key'] for obj in objects.get('Contents', []) if pattern in obj['Key']]
        except Exception as e:
            print(e)
            raise e
        
        
        
        return self._error_messages('not_implemented')


    def dispatch(self, command_string):
        parts = command_string.split(" ")
        response = ''

        if parts[0] == 'createdir':
            # Figure out bucket_name from command_string
            if len(parts) > 1:
                bucket_name = parts[1]
                response = self.createdir(bucket_name)
            else:
                # Parameter Validation
                # - Bucket name is not empty
                # make sure that command
                response = self._error_messages('bucket_name_empty')
        elif parts[0] == 'upload':
            # Figure out parameters from command_string
            # source_file_name and bucket_name are compulsory; dest_object_name is optional
            # Use self._error_messages['incorrect_parameter_number'] if number of parameters is less
            # than number of compulsory parameters
            if len(parts) < 3:
               response = self._error_messages('incorrect_parameter_number')  
            else:
                source_file_name = parts[1]
                bucket_name = parts[2]
                if len(parts) == 4:
                    dest_object_name = parts[3]
                else:
                    dest_object_name = ''
               
                response = self.upload(source_file_name, bucket_name, dest_object_name)
        elif parts[0] == 'download':
            # Figure out parameters from command_string
            # dest_object_name and bucket_name are compulsory; source_file_name is optional
            # Use self._error_messages['incorrect_parameter_number'] if number of parameters is less
            # than number of compulsory parameters
            if len(parts) != 3:
                 response = self._error_messages('incorrect_parameter_number')   
            if len(parts) == 3:
                source_file_name = ''
            else:
                source_file_name = parts[3]
         
            bucket_name = parts[2]
            dest_object_name = parts[1]
            response = self.download(dest_object_name, bucket_name, source_file_name)
        elif parts[0] == 'delete':
            if len(parts) <= 3:
               response = self._error_messages('incorrect_parameter_number')  
            dest_object_name = parts[1]
            bucket_name = parts[2]
            response = self.delete(dest_object_name, bucket_name)
        elif parts[0] == 'deletedir':
            if len(parts) <= 3:
               response = self._error_messages('incorrect_parameter_number')  
            bucket_name = parts[1]
            response = self.deletedir(bucket_name)
        elif parts[0] == 'find':
            if len(parts) < 3:
               response = self._error_messages('incorrect_parameter_number')  
            pattern = parts[1]
            bucket_name = parts[2]
            response = self.find(pattern, bucket_name)
        elif parts[0] == 'listdir':
            bucket_name = ''
            if len(parts) == 2:
                bucket_name = parts[1]
            response = self.listdir(bucket_name)
        else:
            response = "Command not recognized."
        return response


def main():

    s3_handler = S3Handler()
    
    while True:
        try:
            command_string = ''
            if sys.version_info[0] < 3:
                command_string = raw_input("Enter command ('help' to see all commands, 'exit' to quit)>")
            else:
                command_string = input("Enter command ('help' to see all commands, 'exit' to quit)>")
    
            # Remove multiple whitespaces, if they exist
            command_string = " ".join(command_string.split())
            
            if command_string == 'exit':
                print("Good bye!")
                exit()
            elif command_string == 'help':
                s3_handler.help()
            else:
                response = s3_handler.dispatch(command_string)
                print(response)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    main()
