from database.connection import get_connection


class UsuarioDB:

    def obtener_usuarios(self):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                usuario_id,
                usuario_nombre,
                usuario_email,
                usuario_telefono,
                usuario_activo,
                usuario_familiar_nombre,
                usuario_familiar_telefono
                ,usuario_password
            FROM Usuario
        """)

        usuarios = cursor.fetchall()

        conn.close()

        return usuarios

    def registrar_usuario(
        self,
        usuario_id,
        usuario_nombre,
        usuario_email,
        usuario_telefono,
        usuario_activo,
        usuario_familiar_nombre,
        usuario_familiar_telefono,
        usuario_password=None
    ):

        conn = get_connection()

        cursor = conn.cursor()

        sql = """
        INSERT INTO Usuario (
            usuario_id,
            usuario_nombre,
            usuario_email,
            usuario_telefono,
            usuario_activo,
            usuario_familiar_nombre,
            usuario_familiar_telefono,
            usuario_password
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        valores = (
            usuario_id,
            usuario_nombre,
            usuario_email,
            usuario_telefono,
            usuario_activo,
            usuario_familiar_nombre,
            usuario_familiar_telefono,
            usuario_password
        )

        cursor.execute(sql, valores)

        conn.commit()

        conn.close()

    def obtener_usuario_por_email(self, email):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                usuario_id,
                usuario_nombre,
                usuario_email,
                usuario_telefono,
                usuario_activo,
                usuario_familiar_nombre,
                usuario_familiar_telefono,
                usuario_password
            FROM Usuario
            WHERE usuario_email = %s
            LIMIT 1
        """, (email,))

        usuario = cursor.fetchone()
        conn.close()
        return usuario

    def actualizar_telefono(
        self,
        usuario_id,
        nuevo_telefono
    ):

        conn = get_connection()

        cursor = conn.cursor()

        sql = """
        UPDATE Usuario
        SET usuario_telefono = %s
        WHERE usuario_id = %s
        """

        cursor.execute(sql, (
            nuevo_telefono,
            usuario_id
        ))

        conn.commit()

        conn.close()

    def actualizar_nombre(
        self,
        usuario_id,
        nuevo_nombre
    ):

        conn = get_connection()

        cursor = conn.cursor()

        sql = """
        UPDATE Usuario
        SET usuario_nombre = %s
        WHERE usuario_id = %s
        """

        cursor.execute(sql, (
            nuevo_nombre,
            usuario_id
        ))

        conn.commit()

        conn.close()

    def actualizar_usuario(
        self,
        usuario_id,
        nombre=None,
        telefono=None,
        familiar_nombre=None,
        familiar_telefono=None
    ):
        """
        Actualiza múltiples campos del usuario.
        Solo actualiza los campos que se proporcionen.
        """

        conn = get_connection()

        cursor = conn.cursor()

        updates = []
        valores = []

        if nombre is not None:
            updates.append("usuario_nombre = %s")
            valores.append(nombre)

        if telefono is not None:
            updates.append("usuario_telefono = %s")
            valores.append(telefono)

        if familiar_nombre is not None:
            updates.append("usuario_familiar_nombre = %s")
            valores.append(familiar_nombre)

        if familiar_telefono is not None:
            updates.append("usuario_familiar_telefono = %s")
            valores.append(familiar_telefono)

        if not updates:
            conn.close()
            return False

        valores.append(usuario_id)

        sql = f"""
        UPDATE Usuario
        SET {', '.join(updates)}
        WHERE usuario_id = %s
        """

        cursor.execute(sql, valores)

        conn.commit()

        conn.close()

        return True