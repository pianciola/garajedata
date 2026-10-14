"""Consejos automotor: uno por día en la pantalla de inicio.

Cada consejo es (categoría, texto). Son pautas generales y conservadoras: ante la duda, el manual del fabricante manda.
Antes de agregar uno: verificar que sea cierto, que no dependa de una norma que pueda cambiar (o citar la norma)
y que no invite a hacer algo riesgoso. Esta página da consejos, así que cada uno es una responsabilidad.
El consejo del día es el mismo para todos y cambia a la medianoche; recorre todos en un orden fijo (mezclado)
antes de repetir alguno.
"""
from datetime import date
import random

CATEGORIAS = {
    "limpieza": "Limpieza",
    "vial": "Seguridad vial",
    "seguridad": "Seguridad del auto",
    "mantenimiento": "Mantenimiento",
    "ahorro": "Ahorro",
    "datos": "Curiosidad",
    "documentos": "Papeles",
}

CONSEJOS = [
    # ------------------------------------------------------------------ limpieza
    ("limpieza", "Lavá el auto a la sombra y con la chapa fría: el sol y el calor secan el jabón antes de enjuagarlo y dejan manchas."),
    ("limpieza", "Usá shampoo para autos y no detergente de cocina: el detergente saca la cera y reseca la pintura."),
    ("limpieza", "Lavá de arriba hacia abajo: lo más sucio (zócalos, llantas, paragolpes) va al final para no rayar el resto."),
    ("limpieza", "Dos baldes (uno con jabón y otro para enjuagar el guante) evitan arrastrar tierra por toda la pintura y hacer micro rayas."),
    ("limpieza", "Secá con un paño de microfibra limpio: las gamuzas viejas y los trapos de cocina dejan pelusa y rayan."),
    ("limpieza", "Los excrementos de pájaros y los insectos pueden dañar la pintura: sacalos pronto con agua y un paño húmedo, antes de que se sequen y marquen."),
    ("limpieza", "Una buena cera o sellador cada tanto protege la pintura del sol y la lluvia, y hace que la suciedad se limpie más fácil."),
    ("limpieza", "Limpiá las llantas con un producto apto para su material: uno agresivo puede opacar o manchar las de aleación."),
    ("limpieza", "No uses el limpiaparabrisas en seco sobre un vidrio sucio: la tierra actúa como lija. Primero mojá con el líquido."),
    ("limpieza", "Aspirá la alfombra y los asientos antes de pasar paños: la arena y las migas rayan y desgastan la tapicería."),
    ("limpieza", "Para el tablero, un paño apenas húmedo y un limpiador suave; los productos con mucho brillo dan reflejos en el parabrisas."),
    ("limpieza", "Sacudí las alfombras de goma afuera y dejalas secar bien: la humedad atrapada genera olor y oxida el piso."),
    ("limpieza", "Lavar el motor requiere cuidado (conectores, fusibles y alternador no deben mojarse): si no tenés experiencia, dejalo en manos de un lavadero especializado."),
    ("limpieza", "En zonas de mar o con barro y sal en los caminos, lavá también los bajos del auto: la sal acelera el óxido."),
    ("limpieza", "Los vidrios limpios por dentro importan: la película grasosa que deja el plástico del tablero encandila de noche con luces de frente."),
    ("limpieza", "Limpiá las escobillas del limpiaparabrisas con un paño con alcohol o agua jabonosa: se ensucian y dejan rayas en el vidrio."),
    ("limpieza", "Limpiá los burletes de goma de las puertas con un paño húmedo: con tierra y resecos se desgastan antes y dejan pasar agua y ruido."),
    # ------------------------------------------------------------------ seguridad vial
    ("vial", "Dejá siempre una distancia de seguridad: al menos dos segundos con el auto de adelante, y más con lluvia o de noche."),
    ("vial", "Ajustá el apoyacabezas a la altura de la parte alta de la cabeza: es lo que protege el cuello en un choque por atrás."),
    ("vial", "El cinturón va siempre, también atrás. Y debe quedar apoyado en el hombro y la pelvis, nunca sobre el cuello o el abdomen."),
    ("vial", "Los chicos viajan atrás y en su sistema de retención (butaca o elevador) acorde a su edad, peso y altura."),
    ("vial", "El celular se usa con el auto detenido: mirar la pantalla un par de segundos a 100 km/h es recorrer más de cincuenta metros a ciegas."),
    ("vial", "Antes de arrancar, regulá asiento, volante y espejos: ver bien por todos lados evita ángulos ciegos y maniobras inseguras."),
    ("vial", "Con lluvia, bajá la velocidad y evitá frenadas bruscas: el agua aumenta mucho la distancia necesaria para detenerse."),
    ("vial", "En un viaje largo, parate a descansar cada dos horas aproximadamente: el cansancio reduce la atención y los reflejos."),
    ("vial", "En Argentina rige el alcohol cero al volante: si vas a manejar, no tomes. Elegí un conductor designado o un viaje alternativo."),
    ("vial", "En las rutas, llevá siempre las luces bajas encendidas, también de día: es obligatorio y hace que te vean desde más lejos."),
    ("vial", "Señalizá los giros y los cambios de carril con tiempo: las balizas y las luces de giro avisan lo que vas a hacer."),
    ("vial", "En una bajada larga no pongas punto muerto: usá una marcha más corta (o el modo manual, si es automático) para frenar con el motor y no sobrecalentar los frenos."),
    ("vial", "Ante un camión o colectivo, recordá que tienen puntos ciegos grandes: si no ves sus espejos, su conductor no te ve."),
    ("vial", "Mirá lejos: llevá la vista hacia donde querés ir y no sobre el obstáculo, porque tendemos a dirigir el auto hacia donde miramos."),
    ("vial", "De noche, no conduzcas más rápido de lo que alcanzan tus luces: tenés que poder frenar dentro de lo que ves."),
    ("vial", "Cuando te acercás a un cruce, sacá el pie del acelerador y cubrí el freno: reduce el tiempo de reacción si aparece alguien."),
    ("vial", "En una rotonda tiene prioridad quien ya está circulando dentro. Ingresá despacio y señalizá la salida."),
    ("vial", "En la senda peatonal el peatón tiene prioridad: frená antes de la línea, no encima, y no sobrepases a otro auto que se detuvo para dejarlos cruzar."),
    ("vial", "Revisá los puntos ciegos con una mirada rápida por encima del hombro antes de cambiar de carril: los espejos no lo muestran todo."),
    ("vial", "Si tu auto tiene ABS y tenés que frenar a fondo, mantené el pedal pisado: la vibración que sentís es normal, no lo sueltes."),
    ("vial", "Respetar la velocidad máxima no es solo por la multa: la energía de un choque crece con el cuadrado de la velocidad."),
    # ------------------------------------------------------------------ seguridad del auto
    ("seguridad", "Mirá la profundidad del dibujo de los neumáticos: si llegaron a los indicadores de desgaste (TWI), toca cambiarlos."),
    ("seguridad", "Controlá la presión de los neumáticos en frío, al menos una vez al mes. La presión correcta está en la etiqueta de la puerta o en el manual."),
    ("seguridad", "Los neumáticos llevan grabada su fecha de fabricación (4 dígitos: semana y año). Aunque tengan dibujo, el caucho envejece y pierde agarre: si son muy viejos, hacelos revisar."),
    ("seguridad", "Rotar los neumáticos periódicamente alarga su vida y los hace desgastarse parejo."),
    ("seguridad", "Una vibración en el volante a cierta velocidad suele indicar desbalanceo. Se arregla rápido y cuida suspensión y neumáticos."),
    ("seguridad", "Si el auto tira hacia un lado, hay que revisar alineación y presión de neumáticos antes de que el desgaste sea desparejo."),
    ("seguridad", "Los frenos avisan: ruidos metálicos, pedal esponjoso o frenadas más largas son motivos para revisarlos enseguida, sin postergar."),
    ("seguridad", "El líquido de frenos absorbe humedad con el tiempo y pierde eficacia: conviene cambiarlo cada dos años aproximadamente, o lo que indique el fabricante."),
    ("seguridad", "Revisá que todas las luces funcionen (bajas, altas, freno, giro, patente). Pedile a alguien que mire mientras vos probás."),
    ("seguridad", "Tené siempre a mano la rueda de auxilio con presión, el gato y la llave de ruedas. Una auxilio desinflada no sirve."),
    ("seguridad", "Llevá matafuego vigente y balizas, que son obligatorios. El matafuego tiene fecha de carga: renovala antes de que venza."),
    ("seguridad", "Si se enciende la luz roja de aceite o de temperatura, detenete cuanto antes en un lugar seguro y apagá el motor: seguir andando puede arruinarlo. Ante la duda, consultá el manual o pedí asistencia."),
    ("seguridad", "Las escobillas gastadas dejan rayas y puntos ciegos con lluvia. Cambialas una vez al año, aunque parezcan andar."),
    ("seguridad", "Un parabrisas con una piedrita se arregla barato; con el tiempo la rajadura crece. Atendela rápido."),
    ("seguridad", "No dejes objetos sueltos pesados adentro del habitáculo: en una frenada brusca se convierten en proyectiles."),
    ("seguridad", "Para prevenir robos: no dejes nada a la vista (mochilas, celular, cargadores) y no guardes los documentos en el auto cuando lo dejás estacionado."),
    ("seguridad", "Estacioná en lugares iluminados y transitados. Una traba mecánica visible (volante o palanca) desalienta robos oportunistas."),
    ("seguridad", "Al bajar del auto, cerrá con llave siempre, aunque sea un minuto, y controlá que las ventanillas estén cerradas."),
    ("seguridad", "Si usás una llave con control remoto, cuidá el llavero: no lo dejes cerca de la puerta de casa si estacionás en la calle."),
    ("seguridad", "Antes de salir en una ruta larga, revisá aceite, agua del radiador, líquido de frenos, líquido limpiaparabrisas y neumáticos."),
    ("seguridad", "Si sentís olor a nafta o humo dentro del auto, detenete en un lugar seguro, apagá el motor, no fumes ni uses llamas cerca y pedí una revisión: puede ser una pérdida de combustible."),
    ("seguridad", "Los airbags y los cinturones funcionan juntos: sin cinturón puesto, el airbag puede lastimar en lugar de proteger."),
    ("seguridad", "Si llevás GNC, hacé las revisiones periódicas del equipo y de los cilindros en un taller habilitado, y respetá los vencimientos de la oblea."),
    ("seguridad", "Los espejos mal regulados generan ángulos ciegos: regulalos hasta apenas ver el costado del auto."),
    # ------------------------------------------------------------------ mantenimiento
    ("mantenimiento", "Cambiá el aceite y el filtro según el manual (o antes si manejás mucho en ciudad, con calor o en trayectos cortos)."),
    ("mantenimiento", "Controlá el nivel de aceite una vez al mes y antes de los viajes largos, con el auto en terreno plano y siguiendo las indicaciones de tu manual (algunos piden el motor frío y otros recién apagado)."),
    ("mantenimiento", "No hace falta calentar el motor mucho tiempo parado: lo mejor es arrancar y manejar suave hasta que tome temperatura."),
    ("mantenimiento", "La correa de distribución no avisa antes de romperse y puede dañar gravemente el motor: cambiala según los kilómetros o los años que indique el fabricante. (Los motores con cadena de distribución tienen otras pautas.)"),
    ("mantenimiento", "El filtro de aire sucio hace que el motor consuma más y rinda menos. Mirarlo es fácil y cambiarlo, barato."),
    ("mantenimiento", "El filtro de habitáculo (polen) se cambia cada año aproximadamente: si el aire acondicionado huele mal o sale poco aire, empezá por ahí."),
    ("mantenimiento", "Usá refrigerante en la proporción y del tipo que indica el fabricante. El agua sola favorece el óxido y no protege del frío."),
    ("mantenimiento", "Las bujías gastadas hacen que el auto arranque mal, tironee y gaste más nafta. Respetá el intervalo del manual."),
    ("mantenimiento", "La batería suele durar entre tres y cinco años. Si el arranque se vuelve lento, probala antes de quedarte tirado."),
    ("mantenimiento", "Un cable o un borne de batería flojos o sulfatados pueden dejarte sin arranque aunque la batería esté bien. Limpiá los bornes."),
    ("mantenimiento", "El aire acondicionado conviene usarlo un rato aunque sea invierno: así el compresor y los sellos no se resecan."),
    ("mantenimiento", "Mirá debajo del auto después de estacionar: manchas nuevas de aceite, refrigerante o líquido de frenos son la primera señal de una pérdida. (El agua clara que gotea del aire acondicionado es normal.)"),
    ("mantenimiento", "Si el auto va a quedar parado semanas, dejalo con el tanque bastante lleno, en un lugar seco y, si podés, con la batería desconectada. Consultá el manual por otras recomendaciones."),
    ("mantenimiento", "Los amortiguadores desgastados alargan la frenada y dañan neumáticos: si el auto rebota de más al pasar un pozo, revisalos."),
    ("mantenimiento", "Anotar cada service (fecha, kilómetros y qué se hizo) ayuda a vender mejor el auto y a no olvidarse de nada. ¡Para eso está esta bitácora!"),
    ("mantenimiento", "Un ruido nuevo suele significar algo. Cuanto antes lo revise un mecánico, más barato suele ser el arreglo."),
    ("mantenimiento", "Los sensores de oxígeno y otros componentes del escape se ensucian: un mal consumo o una luz de motor encendida piden diagnóstico."),
    ("mantenimiento", "Lubricá cada tanto las bisagras de las puertas, el capó y el baúl: evita ruidos y que se traben."),
    ("mantenimiento", "Si el volante se siente duro o hace ruidos al girar, hacé revisar la dirección: es una pieza de seguridad y conviene no postergarlo."),
    ("mantenimiento", "Después de lavar el auto, pisá el freno despacio un par de veces: el agua en los discos pierde efecto rápido y se recupera la frenada."),
    # ------------------------------------------------------------------ ahorro
    ("ahorro", "Manejar suave ahorra combustible: acelerá y frená gradualmente y anticipate al tránsito."),
    ("ahorro", "Los neumáticos con menos presión consumen más nafta. Mantener la presión correcta es la forma más barata de ahorrar."),
    ("ahorro", "Sacá del baúl lo que no usás: cada cien kilos extra aumenta el consumo de forma apreciable."),
    ("ahorro", "El portaequipajes en el techo aumenta la resistencia al aire. Si no lo usás, sacalo y vas a gastar menos."),
    ("ahorro", "A velocidad de ruta, las ventanillas abiertas aumentan la resistencia al aire y el consumo: conviene cerrarlas."),
    ("ahorro", "En paradas largas y seguras (por ejemplo, esperando a alguien) apagar el motor ahorra combustible. No lo hagas en medio del tránsito."),
    ("ahorro", "Usá la marcha más alta posible sin que el motor vaya forzado o con tirones: las revoluciones bajas ahorran combustible."),
    ("ahorro", "Juntar varias diligencias en un solo viaje ayuda a ahorrar: con el motor frío se consume más."),
    ("ahorro", "Un auto bien mantenido (filtros, bujías, neumáticos) puede consumir menos que uno descuidado."),
    ("ahorro", "Evitá andar siempre con la reserva: la bomba de nafta se refrigera con el combustible y el fondo del tanque puede tener sedimentos."),
    # ------------------------------------------------------------------ datos curiosos
    ("datos", "El Benz Patent-Motorwagen, patentado en 1886, se considera el primer automóvil construido como tal con un motor de combustión interna."),
    ("datos", "El cinturón de seguridad de tres puntos que usamos hoy fue patentado por Volvo en 1959 y se dejó libre para que todas las marcas lo usaran."),
    ("datos", "El ABS evita que las ruedas se bloqueen al frenar fuerte, y así podés seguir girando el volante mientras frenás."),
    ("datos", "El Ford T, lanzado en 1908, llegó a producirse en más de quince millones de unidades, y desde 1913 se armó en una línea de montaje móvil."),
    ("datos", "Los neumáticos son negros porque se les agrega negro de humo, que los hace más resistentes y duraderos."),
    ("datos", "Un neumático solo apoya sobre el piso una superficie parecida a la palma de una mano, y de ahí depende todo el agarre del auto."),
    ("datos", "Los odómetros antiguos funcionaban con un cable que giraba con la caja de cambios; los modernos son electrónicos."),
    ("datos", "En un auto con motor naftero, el catalizador transforma gran parte de los gases tóxicos del escape en otros menos dañinos."),
    ("datos", "El airbag se infla en unas pocas centésimas de segundo, más rápido de lo que dura un parpadeo."),
    ("datos", "El primer semáforo de la historia se instaló en Londres en 1868, antes de que existiera el automóvil; funcionaba con gas."),
    ("datos", "La palabra «automóvil» viene del griego «autos» (por sí mismo) y del latín «mobilis» (que se mueve)."),
    ("datos", "El primer auto eléctrico se construyó en el siglo XIX, antes de que los de nafta dominaran el mercado."),
    ("datos", "El motor Diésel lleva el nombre de Rudolf Diesel, el ingeniero alemán que lo patentó en 1892."),
    ("datos", "Las patentes con formato de letras y números, como las del Mercosur, existen para identificar a cada vehículo de forma única."),
    ("datos", "Los autos modernos llevan millones de líneas de código: el software es una parte clave del vehículo."),
    ("datos", "La suspensión de un auto trabaja casi todo el tiempo: se comprime y se estira miles de veces en un solo viaje."),
    ("datos", "Muchos de los primeros automóviles no tenían volante sino una palanca para dirigir, parecida a la caña de un timón."),
    ("datos", "En la mayoría del mundo se maneja por la derecha, pero en países como Reino Unido, Japón o Australia se maneja por la izquierda."),
    # ------------------------------------------------------------------ papeles
    ("documentos", "Al manejar llevá el registro de conducir, la cédula del vehículo y el seguro vigente. Tener copias en la bóveda de GarajeData sirve de respaldo, pero no reemplaza lo que exija la autoridad."),
    ("documentos", "La VTV tiene fecha de vencimiento (depende de la jurisdicción y de la antigüedad del vehículo): cargala en Vencimientos y te avisamos antes."),
    ("documentos", "Pagá la patente y el seguro al día: un auto con deudas puede tener problemas para transferirse."),
    ("documentos", "Antes de comprar un usado, pedí el informe de dominio y revisá multas e historial de service. Una bitácora ordenada es oro."),
    ("documentos", "El seguro obligatorio por ley cubre daños a terceros. Evaluá una cobertura mayor según el valor y el uso del auto."),
    ("documentos", "Guardá las facturas de los servicios importantes: acreditan el mantenimiento y le dan valor al auto al venderlo."),
    ("documentos", "Si vendés el auto, hacé la transferencia a tiempo y avisá a la aseguradora: así evitás que te lleguen multas o reclamos del nuevo dueño."),
    ("documentos", "Controlá el vencimiento de tu licencia de conducir con tiempo: renovarla lleva turnos y trámites."),
]


def ordenados():
    """Los consejos en un orden fijo mezclado: así el del día no sigue el orden de las categorías."""
    orden = list(range(len(CONSEJOS)))
    random.Random(2026).shuffle(orden)
    return orden


_ORDEN = ordenados()


def consejo_del_dia(hoy=None, salto=0):
    """(índice, categoría, texto): el consejo de hoy; salto=1,2… da los siguientes («ver otro»)."""
    hoy = hoy or date.today()
    pos = (hoy.toordinal() + salto) % len(_ORDEN)
    i = _ORDEN[pos]
    return i, CONSEJOS[i][0], CONSEJOS[i][1]
