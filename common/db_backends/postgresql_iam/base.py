import boto3
from django.db.backends.postgresql import base
from botocore.exceptions import NoCredentialsError, BotoCoreError

class DatabaseWrapper(base.DatabaseWrapper):
    def get_connection_params(self):
        params = super().get_connection_params()
        
        # Determine if we should use IAM authentication (from options)
        options = self.settings_dict.get('OPTIONS', {})
        use_iam_auth = options.get('use_iam_auth', False)
        
        # Remove custom options so psycopg doesn't complain
        params.pop('use_iam_auth', None)
        params.pop('aws_region', None)
        
        if use_iam_auth:
            region = options.get('aws_region', 'us-east-2')
            try:
                client = boto3.client('rds', region_name=region)
                token = client.generate_db_auth_token(
                    DBHostname=params.get('host'),
                    Port=params.get('port', 5432),
                    DBUsername=params.get('user'),
                    Region=region
                )
                params['password'] = token
                # RDS requires SSL for IAM authentication
                params['sslmode'] = 'require'
            except (NoCredentialsError, BotoCoreError) as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Failed to generate IAM DB token: %s", e)
                # Fallback to the configured password if IAM generation fails (useful for local development)
        
        return params
