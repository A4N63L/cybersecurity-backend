#!/bin/sh
set -eu
: "${LDAP_ADMIN_PASSWORD:?Configura LDAP_ADMIN_PASSWORD}"
: "${ALICE_PASSWORD:?Configura ALICE_PASSWORD}"
: "${BOB_PASSWORD:?Configura BOB_PASSWORD}"
host=ldap://openldap:389
dn=cn=admin,dc=example,dc=com
attempt=0
until ldapsearch -x -H "$host" -D "$dn" -w "$LDAP_ADMIN_PASSWORD" -b dc=example,dc=com -s base >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  [ "$attempt" -lt 60 ] || { echo 'LDAP no está disponible'; exit 1; }
  sleep 2
done
# No volver a aplicar el LDIF cuando el directorio ya está completo.
if ! ldapwhoami -x -H "$host" -D uid=alice,ou=users,dc=example,dc=com -w "$ALICE_PASSWORD" >/dev/null 2>&1 ||
   ! ldapwhoami -x -H "$host" -D uid=bob,ou=users,dc=example,dc=com -w "$BOB_PASSWORD" >/dev/null 2>&1; then
  # En una carga parcial, -c permite continuar ante entradas ya existentes.
  # Base64 LDIF evita inyección de líneas o caracteres especiales. Sin archivo
  # renderizado persistente y sin imprimir las contraseñas en los logs.
  alice64=$(printf '%s' "$ALICE_PASSWORD" | base64 | tr -d '\n')
  bob64=$(printf '%s' "$BOB_PASSWORD" | base64 | tr -d '\n')
  sed -e "s|@ALICE_PASSWORD_BASE64@|$alice64|g" -e "s|@BOB_PASSWORD_BASE64@|$bob64|g" /init/users.ldif.template |
    ldapadd -c -x -H "$host" -D "$dn" -w "$LDAP_ADMIN_PASSWORD" || true
fi
for user in alice bob; do
  case "$user" in alice) password=$ALICE_PASSWORD ;; bob) password=$BOB_PASSWORD ;; esac
  ldapwhoami -x -H "$host" -D "uid=$user,ou=users,dc=example,dc=com" -w "$password"
  ldapsearch -x -H "$host" -D "$dn" -w "$LDAP_ADMIN_PASSWORD" -b ou=users,dc=example,dc=com "(uid=$user)" | grep -q "^uid: $user$"
done
echo 'LDAP inicializado y binds de alice/bob verificados.'
