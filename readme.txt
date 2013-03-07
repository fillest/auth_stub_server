# Auth stub server
Example: load test your OAuth authentication system using host substitution with a stub server. 

## Setup
```
pip install -r requirements.txt
python run.py
```
### SSL for nginx
```
cd ~/proj/auth_stub_server
openssl genrsa -des3 -out server.key 1024
openssl req -new -key server.key -out server.csr
cp server.key server.key.org
openssl rsa -in server.key.org -out server.key
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

sudo ln -s /home/f/proj/auth_stub_server/nginx.conf /etc/nginx/sites-enabled/auth_stub_server
sudo /etc/init.d/nginx restart
curl --insecure https://localhost/

# (for testing)
cp config.json.example config.json
# edit the config
```

## License
See licence.txt ([The MIT License](http://www.opensource.org/licenses/mit-license.php))
