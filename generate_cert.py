from OpenSSL import crypto

key = crypto.PKey()
key.generate_key(crypto.TYPE_RSA, 2048)

cert = crypto.X509()
cert.get_subject().C = "IN"
cert.get_subject().ST = "Tamil Nadu"
cert.get_subject().L = "Chennai"
cert.get_subject().O = "QuizServer"
cert.get_subject().OU = "QuizSystem"
cert.get_subject().CN = "localhost"

cert.set_serial_number(1000)
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(365*24*60*60)
cert.set_issuer(cert.get_subject())
cert.set_pubkey(key)
cert.sign(key, 'sha256')

with open("server.crt", "wb") as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

with open("server.key", "wb") as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

print("SSL certificate generated successfully!")