"""Términos y Condiciones y Política de Privacidad de GarajeData.

Adaptados de los de MacroCenter al marco normativo argentino (Ley N.º 25.326 de Protección de los Datos
Personales y su Decreto Reglamentario N.º 1558/2001, Ley N.º 11.723 de Propiedad Intelectual, Ley N.º 24.240 de
Defensa del Consumidor, Código Civil y Comercial de la Nación). Describen lo que la aplicación hace realmente:
cuentas con usuario y contraseña (sin email), datos que carga cada persona, archivos en una bóveda privada, links
opcionales de solo lectura, copias de seguridad diarias, ninguna publicidad ni estadísticas de terceros.

IMPORTANTE: es un texto base. Antes de abrir el sitio al público en general conviene que lo revise un/a abogado/a
(en especial el domicilio y el medio de contacto, que se completan en CONTACTO y DOMICILIO).

Si cambia lo que la app hace con los datos, hay que cambiar este texto y la fecha de ACTUALIZACION.
"""

MARCA = "GarajeData"
RESPONSABLE = "Juan Manuel Pianciola"
ACTUALIZACION = "16 de octubre de 2026"
CONTACTO = "juanpianciola06@gmail.com"
DOMICILIO = "Ciudad Autónoma de Buenos Aires"

_CONTACTO_TXT = (f"Podés comunicarte a **{CONTACTO}**." if CONTACTO
                 else "Podés comunicarte por el canal de contacto que el responsable del sitio informe donde se publique "
                      "esta aplicación.")

TERMINOS = {
    "titulo": "Términos y Condiciones de Uso",
    "intro": (f"Estos Términos y Condiciones regulan el acceso y el uso de **{MARCA}** (en adelante, «el Sitio» o «la Aplicación»), "
              f"una bitácora digital para llevar el historial de mantenimiento de vehículos, desarrollada y administrada por "
              f"**{RESPONSABLE}** (en adelante, «el Responsable»). Al crear una cuenta o utilizar el Sitio, el usuario declara haber "
              "leído, comprendido y aceptado estos Términos y la Política de Privacidad. Si no está de acuerdo, deberá abstenerse "
              "de utilizarlo."),
    "secciones": [
        ("1. Objeto y descripción del servicio",
         ["El Sitio ofrece, de manera gratuita, un espacio para que cada persona registre los services, controles, reparaciones, "
          "fluidos, piezas y modificaciones de sus vehículos, guarde sus vencimientos (VTV, seguro, patente, matafuegos, licencia) y "
          "documentos en una bóveda privada, vea estadísticas de gasto y reciba recordatorios, y genere un libro de servicio en PDF y "
          "links de solo lectura para compartir su historial."]),
        ("2. Cuenta de usuario",
         ["Para usar el Sitio hay que crear una cuenta con un nombre de usuario y una contraseña. No se solicita correo electrónico "
          "ni datos de identidad. Al crearla se entrega un **código de recuperación** que se muestra una sola vez: es la única "
          "forma de recuperar el acceso si se pierde la contraseña, porque el Sitio no conoce ningún correo ni dato de contacto de "
          "la persona. **Si se pierden la contraseña y el código, la cuenta no puede recuperarse.**",
          "Cada usuario es responsable de mantener en secreto su contraseña y su código de recuperación, y de toda la actividad que "
          "se realice con su cuenta. Se debe avisar al Responsable ante cualquier uso no autorizado. Se admite una cuenta por "
          "persona y el Sitio puede limitar la creación de cuentas nuevas (por ejemplo, por cantidad desde una misma conexión o por "
          "cupo total del servicio)."]),
        ("3. Carácter informativo: el Sitio no es un registro oficial",
         ["La bitácora es un **registro privado y declarativo**: contiene lo que el propio usuario carga. El Sitio no verifica que "
          "los datos, kilometrajes, fechas, costos o archivos sean ciertos, y no reemplaza ningún registro, certificado ni "
          "documento oficial (por ejemplo, los del Registro Nacional de la Propiedad del Automotor, la verificación técnica, la "
          "compañía de seguros o el fabricante).",
          "El «certificado de historial» y el libro de servicio en PDF son una **constancia informativa** generada con los datos "
          "cargados por el usuario. No son un certificado oficial ni tienen valor de prueba por sí solos, y el número que llevan "
          "no implica que el Responsable haya revisado ni garantizado su contenido. Quien los reciba debe tomarlos como lo que "
          "son: información declarada por el dueño del vehículo."]),
        ("4. Recordatorios y estimaciones",
         ["Los avisos de próximos controles, el plan de mantenimiento, los kilómetros estimados, los vencimientos y las "
          "estadísticas son cálculos **orientativos** hechos con lo que el usuario cargó y con criterios generales (por ejemplo, un "
          "perfil de uso elegido por la persona). No reemplazan el manual del fabricante, la indicación de un mecánico ni las "
          "obligaciones legales del conductor. Pueden contener errores o no llegar a tiempo.",
          "El usuario es el único responsable de realizar los controles de su vehículo y de renovar sus documentos y "
          "habilitaciones a tiempo. El Responsable no responde por multas, infracciones, fallas mecánicas, accidentes ni "
          "perjuicios derivados de un aviso que no se mostró, llegó tarde o fue inexacto."]),
        ("4 bis. Datos de garaje y consejos",
         ["El «dato de garaje» del día y los demás consejos, datos curiosos y recordatorios sobre trámites del Sitio son **información general y orientativa**, pensada para "
          "promover el cuidado del vehículo y la seguridad vial. No reemplazan el manual del fabricante, la indicación de un "
          "mecánico o profesional matriculado, ni las normas de tránsito vigentes, que pueden cambiar. Cada persona es "
          "responsable de las decisiones que tome sobre su vehículo. Se procura que sean correctos; si encontrás uno "
          "dudoso o desactualizado, avisá al contacto de este documento."]),
        ("5. Contenido del usuario",
         ["El usuario conserva la titularidad de todo lo que carga (datos, textos, fotos y documentos) y es el único responsable de "
          "su contenido. Declara que tiene derecho a cargarlo y que no vulnera derechos de terceros ni la ley. Se recomienda no "
          "subir documentos que contengan datos personales de otras personas sin su consentimiento.",
          "El usuario otorga al Responsable la autorización limitada y no exclusiva necesaria para almacenar, procesar y mostrar ese "
          "contenido **al propio usuario y a quienes él decida**, con el único fin de prestar el servicio. Las fotos se "
          "redimensionan y se les eliminan los metadatos (como la ubicación GPS) al subirlas. Cada cuenta dispone de un espacio de "
          "almacenamiento limitado (100 MB al momento de esta versión)."]),
        ("6. Links para compartir y calendario",
         ["El usuario puede crear un **link de solo lectura** de un vehículo y un **link de calendario** con sus próximos "
          "vencimientos. Quien tenga el link puede ver esa información sin iniciar sesión. Los links son secretos y de difusión "
          "bajo exclusiva responsabilidad del usuario: conviene compartirlos solo con personas de confianza y desactivarlos cuando "
          "ya no hagan falta. El link de solo lectura nunca incluye la documentación, los vencimientos ni la bóveda."]),
        ("7. Transferencia de vehículos",
         ["El usuario puede transferir un vehículo, con toda su historia (registros, documentación, bóveda y fotos), a otra cuenta "
          "mediante un código de un solo uso que vale por tiempo limitado. **Quien recibe el vehículo pasa a ser su único "
          "titular dentro del Sitio** y el dueño anterior deja de tener acceso. La transferencia no implica ni acredita una "
          "transferencia de dominio del vehículo, que se rige por la ley y los registros oficiales. El usuario que genera el "
          "código es responsable de entregarlo únicamente a quien corresponda."]),
        ("8. Propiedad intelectual",
         [f"El diseño, la marca y el logotipo de {MARCA}, el código fuente, la estructura y los textos propios son propiedad de "
          f"{RESPONSABLE} y están protegidos por la Ley N.º 11.723 de Propiedad Intelectual y demás normas aplicables. Queda "
          "prohibida su reproducción, distribución, modificación o uso comercial sin autorización previa y por escrito.",
          "Las marcas y logotipos de fabricantes de automotores pertenecen a sus titulares y se usan solo para identificar el "
          "vehículo cargado por el usuario, sin que ello implique relación alguna con ellos. Los modelos 3D genéricos "
          "se utilizan según su licencia (Creative Commons BY 4.0), con los créditos indicados al pie del Sitio."]),
        ("9. Uso permitido",
         ["El usuario se compromete a utilizar el Sitio de buena fe y conforme a la ley. Queda prohibido: (a) intentar acceder sin "
          "autorización a cuentas, datos o sistemas, o vulnerar o eludir medidas de seguridad; (b) realizar extracciones masivas o "
          "automatizadas, o crear cuentas de forma automática; (c) subir código malicioso o archivos que no sean fotos o PDF "
          "propios del servicio; (d) usar el Sitio para almacenar o difundir contenido ilícito, ofensivo o que viole derechos de "
          "terceros; (e) presentar datos falsos como si fueran verificados para engañar a un tercero, por ejemplo, al vender un "
          "vehículo; y (f) usar el Sitio para fines ilícitos.",
          "El Responsable podrá suspender o eliminar cuentas y contenidos que incumplan estos Términos, o cuentas sin actividad por "
          "un tiempo prolongado, procurando avisar cuando sea posible. Para evitar pérdidas, se recomienda descargar periódicamente "
          "una copia de los datos desde «Mi cuenta»."]),
        ("10. Enlaces y servicios de terceros",
         ["El Sitio puede incluir enlaces o botones que llevan a servicios de terceros (por ejemplo, para enviar un link por "
          "WhatsApp) y se apoya en un proveedor de alojamiento. "
          "El Responsable no controla ni responde por su contenido, disponibilidad ni prácticas de privacidad."]),
        ("11. Disponibilidad del servicio y copias de seguridad",
         ["El servicio se presta «tal como está», de forma gratuita y según disponibilidad. El Responsable no garantiza el "
          "funcionamiento ininterrumpido, la ausencia de errores ni la conservación de los datos. Se realizan copias de "
          "seguridad diarias de la base de datos, pero **no se garantiza que los datos puedan restaurarse** ni se respaldan los "
          "archivos subidos. Podrá modificar, suspender o discontinuar total o parcialmente el Sitio en cualquier momento, sin que "
          "ello genere derecho a indemnización; en ese caso se procurará avisar con anticipación para que los usuarios descarguen "
          "sus datos."]),
        ("12. Limitación de responsabilidad",
         ["En la máxima medida permitida por la legislación vigente, el Responsable no será responsable por daños directos o "
          "indirectos, lucro cesante, pérdida de oportunidades o de datos derivados del uso o de la imposibilidad de uso del Sitio, "
          "de la información cargada por los usuarios o del uso que otros hagan de los links y documentos compartidos por el "
          "propio usuario. Lo dispuesto en esta cláusula no afecta los derechos irrenunciables que la Ley N.º 24.240 de Defensa "
          "del Consumidor y el Código Civil y Comercial de la Nación reconocen a los usuarios que revistan el carácter de "
          "consumidores."]),
        ("13. Protección de datos personales",
         ["El tratamiento de la información se rige por la Política de Privacidad, que forma parte integrante de estos Términos."]),
        ("14. Modificaciones",
         ["El Responsable podrá modificar estos Términos en cualquier momento. La versión vigente será la publicada en el Sitio, "
          "con indicación de su fecha de actualización. El uso continuado del Sitio implica la aceptación de los cambios."]),
        ("15. Ley aplicable y jurisdicción",
         ["Estos Términos se rigen por las leyes de la República Argentina. Toda controversia será sometida a los tribunales "
          "ordinarios competentes de la República Argentina. Cuando el usuario sea consumidor, será competente el tribunal del "
          "lugar de su domicilio o el que resulte de las normas de orden público aplicables."]),
        ("16. Contacto",
         [_CONTACTO_TXT + (f" Domicilio: {DOMICILIO}." if DOMICILIO else "")]),
    ],
}

PRIVACIDAD = {
    "titulo": "Política de Privacidad",
    "intro": (f"La presente Política de Privacidad describe cómo **{MARCA}** trata la información de quienes lo utilizan, en "
              "cumplimiento de la Ley N.º 25.326 de Protección de los Datos Personales, su Decreto Reglamentario N.º 1558/2001 y "
              f"demás normativa aplicable. El responsable del tratamiento es **{RESPONSABLE}**."),
    "secciones": [
        ("1. Qué datos tratamos",
         ["**No pedimos correo electrónico, teléfono, nombre real, documento ni datos de pago.** Tratamos solamente lo siguiente:",
          "**Datos de la cuenta:** el nombre de usuario que elige la persona y su contraseña, que se guarda **cifrada** (no es posible "
          "leerla). Lo mismo ocurre con el código de recuperación, que se guarda cifrado y se muestra una sola vez. Conviene elegir "
          "un nombre de usuario que no revele quién sos. Si la persona sube una **foto de perfil** (opcional), se guarda "
          "recortada y sin metadatos (como la ubicación), la ve solo ella y se borra al quitarla o al borrar la cuenta.",
          "**Datos que carga el usuario:** autos y motos (marca, modelo, patente, VIN, color, kilometraje, cilindrada opcional de la moto y ficha técnica), registros de "
          "mantenimiento y gastos, incluido combustible (fechas, costos, quién hizo el trabajo y notas), vencimientos de documentos y los archivos que sube "
          "(fotos del auto, facturas y documentos de la bóveda, como la cédula o el seguro). Estos datos pueden ser personales "
          "—por ejemplo, la patente o un documento que contenga nombres—, por lo que se recomienda subir solo lo necesario y "
          "no cargar datos de terceros sin su consentimiento.",
          "**Datos técnicos:** la aplicación usa la dirección IP de la conexión únicamente **en memoria y por un tiempo breve** "
          "para limitar la cantidad de cuentas nuevas que se crean desde una misma conexión y los intentos de ingreso; no se "
          "guarda en la base de datos. El servicio de alojamiento puede registrar datos técnicos de las conexiones (como IP, fecha, "
          "hora y navegador) en sus propios registros de seguridad y diagnóstico.",
          "**Administración:** el responsable del Sitio puede ver la lista de cuentas (nombre de usuario, fecha de creación y "
          "último día de uso) y cantidades de cada una (vehículos, registros y espacio ocupado), para mantener el servicio y "
          "detectar abusos. **No ve el contenido** de los vehículos, registros ni archivos de cada usuario desde la aplicación.",
          "**No usamos** publicidad, herramientas de estadísticas de terceros, huellas digitales ni seguimiento del comportamiento "
          "de los usuarios."]),
        ("2. Cookies y almacenamiento en el dispositivo",
         ["Se usa **una cookie de sesión**, estrictamente necesaria, para mantener la sesión iniciada (hasta 60 días) y proteger los "
          "formularios contra solicitudes falsificadas. No es una cookie publicitaria ni de seguimiento. El servidor guarda "
          "un identificador protegido de cada sesión y su vencimiento para poder revocarla al salir. Cambiar o recuperar "
          "la contraseña invalida todas las sesiones anteriores.",
          "El navegador también guarda, solo en el dispositivo del usuario: preferencias de pantalla (por ejemplo, qué secciones "
          "mostrar en el libro de servicio o qué avisos silenciar) y, para que la bitácora se pueda consultar sin conexión, una "
          "**copia local de las páginas y archivos vistos**. Esa copia se borra al cerrar sesión. En un dispositivo compartido "
          "conviene cerrar sesión siempre."]),
        ("3. Para qué usamos los datos",
         ["Los datos se usan exclusivamente para prestar el servicio: mostrar la bitácora, calcular recordatorios y estadísticas, "
          "generar el libro de servicio y los links que el usuario decida crear, y mantener la seguridad del Sitio. No se "
          "venden, no se alquilan, no se usan para publicidad ni para perfilar usuarios, y el Responsable no los revisa salvo "
          "que sea necesario para resolver una falla, atender un pedido del usuario o cumplir una orden de autoridad competente."]),
        ("4. Quién puede ver tus datos",
         ["**Solo vos**, iniciando sesión con tu cuenta. Los vehículos, registros, documentos y archivos de una cuenta no son visibles "
          "para otras cuentas.",
          "**Excepciones que decide el propio usuario:** (a) quien tenga el **link de solo lectura** de un vehículo ve su historia sin "
          "iniciar sesión (sin la documentación, los vencimientos ni la bóveda; el usuario puede ocultar también costos y fotos); "
          "(b) quien tenga el **link del calendario** ve las fechas de los próximos controles y vencimientos; (c) quien reciba el "
          "**libro de servicio en PDF** que el usuario genere y envíe; y (d) quien reciba un vehículo por **transferencia** pasa a "
          "ser su único titular y accede a toda su historia. Estos links pueden desactivarse o regenerarse en cualquier momento, "
          "y dejan de funcionar."]),
        ("5. Servicios y proveedores de terceros",
         ["**Alojamiento:** el Sitio y la base de datos se alojan en los servidores de **PythonAnywhere** (PythonAnywhere LLP), "
          "que pueden estar ubicados fuera de la Argentina. Al crear una cuenta, el usuario presta su consentimiento expreso a ese "
          "alojamiento.",
          "**Sin servicios externos en el Sitio:** los logos de marcas, las tipografías y los modelos 3D se sirven desde "
          "el propio Sitio, así que al navegar no se envía ningún dato a otros servidores.",
          "**WhatsApp:** el botón para enviar un link solo abre WhatsApp con el mensaje; la información se entrega a ese servicio "
          "únicamente si el usuario decide enviarla. El tratamiento posterior se rige por la política de privacidad del tercero."]),
        ("6. Seguridad",
         ["Se aplican medidas técnicas razonables: contraseñas cifradas, conexión cifrada (HTTPS), protección contra solicitudes "
          "falsificadas entre sitios en todos los formularios, límite de intentos de ingreso y de creación de cuentas, control de que "
          "cada archivo solo pueda abrirlo su dueño, validación del tipo de los archivos subidos y eliminación de los metadatos "
          "de las fotos. Ningún sistema es completamente invulnerable; el Responsable no puede garantizar una seguridad absoluta. "
          "Se recomienda usar una contraseña única y guardar el código de recuperación en un lugar seguro."]),
        ("7. Copias de seguridad y conservación",
         ["Los datos se conservan mientras la cuenta exista. Se realizan **copias de seguridad diarias** de la base de datos, de las que se "
          "guardan las últimas catorce. Por eso, los datos eliminados pueden permanecer en esas copias hasta catorce días más, "
          "después de lo cual se borran definitivamente. Las copias se almacenan en el mismo servicio de alojamiento y se "
          "usan solo para recuperar el Sitio ante una falla."]),
        ("8. Finalidad y base del tratamiento",
         ["El tratamiento se basa en el consentimiento libre, expreso e informado del usuario, que se presta al crear la cuenta y "
          "aceptar estos documentos, y en la necesidad de prestar el servicio solicitado (artículo 5 de la Ley N.º 25.326). El "
          "usuario puede revocar su consentimiento en cualquier momento eliminando su cuenta."]),
        ("9. Transferencias y cesión de datos",
         ["El Responsable no vende, cede ni transfiere datos personales a terceros. El alojamiento en servidores que puedan estar "
          "en el exterior (punto 5) se realiza con el consentimiento expreso del usuario, conforme al artículo 12 de la Ley N.º "
          "25.326. Lo indicado sobre conexiones técnicas del navegador con servicios de terceros no constituye una cesión por "
          "parte del Responsable."]),
        ("10. Tus derechos",
         ["Conforme a los artículos 14, 15 y 16 de la Ley N.º 25.326, el titular de los datos puede ejercer los derechos de acceso "
          "(en forma gratuita a intervalos no inferiores a seis meses, salvo que acredite un interés legítimo), rectificación, "
          "actualización y supresión. **Podés hacerlo vos mismo, sin pedirle nada a nadie, desde «Mi cuenta»:** descargar todos tus "
          "datos (un archivo .zip con tus vehículos, registros —también en planilla para Excel—, vencimientos y archivos), "
          "editar o borrar cualquier dato, **importar** una copia descargada en otra cuenta, y **eliminar tu cuenta** con todo su contenido.",
          "Como el Sitio no conoce la identidad de las personas, para atender un pedido sobre una cuenta el Responsable podrá "
          "pedir que se acredite el control de esa cuenta (por ejemplo, iniciando sesión). Para consultas sobre esta política: "
          + _CONTACTO_TXT[0].lower() + _CONTACTO_TXT[1:],
          "**La AGENCIA DE ACCESO A LA INFORMACIÓN PÚBLICA, en su carácter de Órgano de Control de la Ley N.º 25.326, tiene la "
          "atribución de atender las denuncias y reclamos que interpongan quienes resulten afectados en sus derechos por "
          "incumplimiento de las normas vigentes en materia de protección de datos personales.**"]),
        ("11. Menores de edad",
         ["El Sitio no está dirigido a niños y niñas. Los menores de dieciocho años deben usarlo con la autorización y "
          "supervisión de sus padres o representantes legales."]),
        ("12. Cambios en esta política",
         ["Esta Política puede actualizarse periódicamente. La versión vigente es la publicada en el Sitio, con su fecha de "
          "actualización. Si el cambio altera de manera importante el tratamiento de los datos, se informará dentro del Sitio."]),
    ],
}

PAGINAS = {"terminos": TERMINOS, "privacidad": PRIVACIDAD}
