# Deployment assets

For production HTTPS, provide a certificate and private key through your secret manager. Do not commit either file.

For local development only, generate a self-signed certificate with:

```bash
./deploy/generate-dev-cert.sh
```

A self-signed certificate is not appropriate for public production clients.
