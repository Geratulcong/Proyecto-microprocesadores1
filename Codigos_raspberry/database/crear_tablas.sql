CREATE TABLE Usuario (
    usuario_id CHAR(36) PRIMARY KEY,
    usuario_nombre VARCHAR(80) NOT NULL,
    usuario_email VARCHAR(120) NOT NULL UNIQUE,
    usuario_password VARCHAR(255),
    usuario_telefono VARCHAR(20),
    usuario_activo BOOLEAN,
    usuario_familiar_nombre VARCHAR(80) NOT NULL,
    usuario_familiar_telefono VARCHAR(20)
);

CREATE TABLE Raspberry_PI (
    raspberry_id CHAR(36) PRIMARY KEY,
    usuario_id CHAR(36),
    raspberry_estado_arduino VARCHAR(20),
    raspberry_estado_pagina_web VARCHAR(20),
    raspberry_nivel_bateria DECIMAL(5,2),

    FOREIGN KEY (usuario_id)
    REFERENCES Usuario(usuario_id)
);

CREATE TABLE Contacto_Emergencia (
    contacto_id CHAR(36) PRIMARY KEY,
    usuario_id CHAR(36) NOT NULL,
    contacto_nombre VARCHAR(80) NOT NULL,
    contacto_telefono VARCHAR(20),
    contacto_estado BOOLEAN,

    FOREIGN KEY (usuario_id)
    REFERENCES Usuario(usuario_id)
);

CREATE TABLE Arduino (
    arduino_id CHAR(36) PRIMARY KEY,
    raspberry_id CHAR(36),
    arduino_estado VARCHAR(20),

    FOREIGN KEY (raspberry_id)
    REFERENCES Raspberry_PI(raspberry_id)
);

CREATE TABLE Perfil_Wifi (
    perfil_id CHAR(36) PRIMARY KEY,
    raspberry_id CHAR(36),
    perfil_ssid VARCHAR(100) NOT NULL,
    perfil_seguridad VARCHAR(50),
    perfil_estado BOOLEAN,

    FOREIGN KEY (raspberry_id)
    REFERENCES Raspberry_PI(raspberry_id)
);

CREATE TABLE Evento_Caida (
    evento_id CHAR(36) PRIMARY KEY,
    raspberry_id CHAR(36),
    evento_detectado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evento_tipo VARCHAR(50),

    FOREIGN KEY (raspberry_id)
    REFERENCES Raspberry_PI(raspberry_id)
);

CREATE TABLE Evento_Raspberry (
    evento_raspberry_id CHAR(36) PRIMARY KEY,
    raspberry_id CHAR(36),
    evento_tipo VARCHAR(50),
    evento_detectado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (raspberry_id)
    REFERENCES Raspberry_PI(raspberry_id)
);

CREATE TABLE Notificacion (
    notificacion_id CHAR(36) PRIMARY KEY,
    contacto_id CHAR(36) NOT NULL,
    evento_id CHAR(36),
    evento_raspberry_id CHAR(36),
    notificacion_canal VARCHAR(30),
    notificacion_estado VARCHAR(30),
    notificacion_mensaje TEXT,

    FOREIGN KEY (contacto_id)
    REFERENCES Contacto_Emergencia(contacto_id),

    FOREIGN KEY (evento_id)
    REFERENCES Evento_Caida(evento_id),

    FOREIGN KEY (evento_raspberry_id)
    REFERENCES Evento_Raspberry(evento_raspberry_id)
);