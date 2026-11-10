"""
gerar_certificado.py
Gera o certificado (cliente_cert.der) e a chave privada (cliente_key.pem) do cliente OPC UA.
Executar UMA vez (e novamente sempre que alterar o certificado).
Não compartilhe a chave privada.
"""
import datetime
import ipaddress
import socket

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from config import APP_URI, CERT, CHAVE

# True  -> PLANO A: BasicConstraints cA=true (pathLen=0) + keyCertSign
# False -> PLANO B: certificado sem poder de CA (cA=false, sem keyCertSign)
MODO_CA = True

chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "GatewayReservatorio")])
agora = datetime.datetime.now(datetime.timezone.utc)

usos = x509.KeyUsage(
    digital_signature=True,
    content_commitment=True,          # nonRepudiation
    key_encipherment=True,
    data_encipherment=True,
    key_agreement=False,
    key_cert_sign=MODO_CA,
    crl_sign=False,
    encipher_only=False,
    decipher_only=False,
)

if MODO_CA:
    restricao = x509.BasicConstraints(ca=True, path_length=0)
else:
    restricao = x509.BasicConstraints(ca=False, path_length=None)

cert = (
    x509.CertificateBuilder()
    .subject_name(nome)
    .issuer_name(nome)
    .public_key(chave.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(agora - datetime.timedelta(days=1))
    .not_valid_after(agora + datetime.timedelta(days=3650))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.UniformResourceIdentifier(APP_URI),
            x509.DNSName(socket.gethostname()),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]),
        critical=False,
    )
    .add_extension(usos, critical=True)
    .add_extension(
        x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]),
        critical=False,
    )
    .add_extension(restricao, critical=True)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(chave.public_key()), critical=False)
    .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(chave.public_key()), critical=False)
    .sign(chave, hashes.SHA256())
)

with open(CERT, "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.DER))
with open(CHAVE, "wb") as f:
    f.write(chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

print("Modo:", "A (cA=true, pathLen=0, keyCertSign)" if MODO_CA else "B (cA=false, sem keyCertSign)")
print("Gerados:")
print(" ", CERT)
print(" ", CHAVE)