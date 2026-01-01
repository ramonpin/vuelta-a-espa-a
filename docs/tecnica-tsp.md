# Viajante: Fundamentos Técnicos y Teóricos

## Tabla de Contenidos

1. [Fundamentos del Problema del Viajante (TSP)](#1-fundamentos-del-problema-del-viajante-tsp)
2. [Teoría de Grafos Aplicada](#2-teoría-de-grafos-aplicada)
3. [Programación Lineal Entera (ILP)](#3-programación-lineal-entera-ilp)
4. [Formulación MTZ (Miller-Tucker-Zemlin)](#4-formulación-mtz-miller-tucker-zemlin)
5. [El Solver: PuLP + CBC](#5-el-solver-pulp--cbc)
6. [Técnicas de Visualización](#6-técnicas-de-visualización)
7. [Análisis de Resultados](#7-análisis-de-resultados)
8. [Apéndice A: Glosario de Ciudades](#apéndice-a-glosario-de-ciudades)
9. [Apéndice B: Ejecución del Proyecto](#apéndice-b-ejecución-del-proyecto)

---

## 1. Fundamentos del Problema del Viajante (TSP)

### 1.1 Definición Formal

El **Problema del Viajante** (_Travelling Salesperson Problem_, TSP) es uno de
los problemas de optimización combinatoria más estudiados en ciencias de la
computación e investigación operativa. Dado un conjunto de ciudades y las
distancias entre cada par de ellas, el objetivo es encontrar la ruta más corta
que:

1. Visite **exactamente una vez** cada ciudad.
2. Regrese a la ciudad de origen.
3. Minimice la distancia total recorrida.

Formalmente, dado un grafo ponderado completo $G = (V, E, w)$ donde $V$ es un
conjunto de $n$ nodos (ciudades), $E$ es el conjunto de aristas (conexiones), y
$w: E \to \mathbb{R}^+$ es una función de peso (distancia), el TSP busca el
**ciclo hamiltoniano de peso mínimo**:

$$\min_{C \in \mathcal{H}} \sum_{(i,j) \in C} w_{ij}$$

donde $\mathcal{H}$ es el conjunto de todos los ciclos hamiltonianos en $G$.

### 1.2 Ciclo Hamiltoniano

Un **ciclo hamiltoniano** es un ciclo en un grafo que visita cada vértice
exactamente una vez (y regresa al inicio). La distinción es sutil pero crucial:
mientras el TSP busca el _mejor_ ciclo (mínimo peso), la mera existencia de un
ciclo hamiltoniano es ya un problema NP-completo por sí mismo.

Encontrar un ciclo hamiltoniano en un grafo arbitrario es el **Problema del
Ciclo Hamiltoniano** (HCP), uno de los 21 problemas NP-completos originales de
Karp (1972). El TSP añade la dimensión de optimización sobre esta base,
convirtiéndolo en un problema NP-duro (_NP-Hard_).

### 1.3 Complejidad Computacional

Sea $n = |V|$ el número de ciudades. En un grafo completo (todas las ciudades
conectadas entre sí de forma simétrica), el número de ciclos hamiltonianos
posibles es:

$$|\mathcal{H}| = \frac{(n-1)!}{2}$$

Para $n = 47$ (las capitales de provincia españolas peninsulares):

$$|\mathcal{H}| = \frac{46!}{2} \approx 2.75 \times 10^{57}$$

Este número es astronómicamente grande. Para ponerlo en perspectiva:

- Es aproximadamente $10^{31}$ veces mayor que el número de estrellas estimadas
  en el universo observable ($\sim 10^{24}$).
- Es mayor que el número de átomos en la Tierra ($\sim 10^{50}$).
- Aunque tuviéramos un supercomputador capaz de evaluar $10^{15}$ rutas por
  segundo (1 peta-ruta/s), necesitaríamos $\sim 8.7 \times 10^{33}$ años — **mil
  millones de veces la edad del universo** — para evaluarlas todas por fuerza
  bruta.

Sin embargo, esta cota corresponde a un **grafo completo**, donde cualquier
ciudad está conectada con cualquier otra. La realidad de este proyecto es
radicalmente distinta, como veremos en la siguiente sección.

### 1.4 TSP en Grafos Dispersos vs. Completos

| Propiedad           | Grafo Completo         | Grafo de Carreteras Real                          |
| ------------------- | ---------------------- | ------------------------------------------------- |
| Aristas potenciales | $\binom{n}{2} = 1081$  | $\sim 110$ únicas (bidireccionales)               |
| Densidad            | $1.0$ (100%)           | $\sim 0.10$ (10%)                                 |
| Grado promedio      | $n-1 = 46$             | $\sim 4.68$                                       |
| Rutas hamiltonianas | $\frac{(46)!}{2}$      | Muchas menos                                      |
| Dificultad          | NP-duro (optimización) | NP-completo (existencia) + NP-duro (optimización) |

En nuestro caso, el grafo es **disperso y restringido**: las conexiones
representan carreteras reales entre provincias adyacentes geográficamente. Esto
significa que:

1. El número de rutas hamiltonianas válidas es **muchísimo menor** que en un
   grafo completo.
2. Puede que **no exista ningún ciclo hamiltoniano** si la red no está
   suficientemente conectada.
3. El problema es más restrictivo y, en cierto sentido, más difícil de modelar
   porque añade restricciones topológicas reales.

---

## 2. Teoría de Grafos Aplicada

### 2.1 Representación del Grafo

#### 2.1.1 El archivo `network.txt`

El grafo se almacena en un archivo tabulado de tres columnas:

```
Origen  Destino  Distancia
M       AV       110.3
M       CU       173.3
M       GU       64.2
...
```

Contiene **219 líneas** de datos (más la cabecera), donde cada conexión entre
dos nodos aparece **dos veces** (una en cada dirección, p.ej. `A → AB` con 174.4
km y `AB → A` con 174.4 km). La red representa 47 nodos y aproximadamente 110
conexiones únicas bidireccionales.

#### 2.1.2 Codificación en `solve_tsp.py`

El grafo se carga como un **diccionario de aristas dirigidas**:

```python
edges = {}
nodes = set()

for row in reader:
    u, v, w = row[0].strip(), row[1].strip(), float(row[2].strip())
    edges[(u, v)] = w        # Arista dirigida u → v
    edges[(v, u)] = w        # Arista dirigida v → u (simetría manual)
    nodes.add(u)
    nodes.add(v)
```

Esto significa que, aunque el grafo real es no dirigido (la distancia de A a B
es la misma que de B a A), se modela como un **grafo dirigido** con aristas en
ambas direcciones. Esta elección es intencionada: el modelo ILP (como veremos en
§3) utiliza variables de decisión binarias $x_{ij}$ que representan el
movimiento _direccional_ entre ciudades. Tener aristas en ambas direcciones es
necesario para que el TSP pueda decidir en qué sentido recorre una conexión.

#### 2.1.3 Tipos de Grafos y su Relevancia

| Tipo de Grafo    | Definición                                       | En este proyecto               |
| ---------------- | ------------------------------------------------ | ------------------------------ |
| **No dirigido**  | $(u,v) \in E \iff (v,u) \in E$ y $w(u,v)=w(v,u)$ | El grafo real lo es            |
| **Dirigido**     | $(u,v) \neq (v,u)$ potencialmente                | Así se modela en el ILP        |
| **Simple**       | Sin bucles ni aristas múltiples                  | Cumple                         |
| **Ponderado**    | Cada arista tiene un peso $w_{ij}$               | Distancias en km               |
| **Conexo**       | Existe camino entre cualquier par de nodos       | **Sí** (verificado)            |
| **Hamiltoniano** | Contiene al menos un ciclo hamiltoniano          | **Sí** (probado por el solver) |

El grafo es **conexo** porque de lo contrario sería imposible encontrar un ciclo
hamiltoniano (condición necesaria, aunque no suficiente). La conexidad no se
verifica explícitamente en el código, pero está implícitamente probada puesto
que el solver encontró una solución óptima.

### 2.2 Grado de Conectividad

El **grado** de un nodo $v$, denotado $\deg(v)$, es el número de aristas
incidentes sobre él. Es una medida fundamental de la conectividad local.

#### 2.2.1 Distribución de Grados

El script `connectivity.py` calcula esta distribución contando las conexiones
salientes de cada nodo en el grafo dirigido:

```
Nodo       Conexiones (Grado)
───────────────────────────────────────────
CU         9
AB         8
BU         8
BU         8
...
```

El rango de grados típicamente varía entre 2 (nodos periféricos) y ~9 (nodos
centrales bien conectados como Cuenca o Albacete).

#### 2.2.2 Condiciones de Existencia de Ciclos Hamiltonianos

Existen teoremas clásicos que garantizan la existencia de un ciclo hamiltoniano
basados en el grado mínimo:

- **Teorema de Dirac (1952)**: Si $\forall v \in V: \deg(v) \geq n/2$, entonces
  $G$ es hamiltoniano.
- **Teorema de Ore (1960)**: Si para todo par de vértices no adyacentes $u, v$
  se cumple $\deg(u) + \deg(v) \geq n$, entonces $G$ es hamiltoniano.
- **Teorema de Chvátal (1972)**: Condición de cierre basada en la secuencia de
  grados ordenada.

Para $n = 47$, el teorema de Dirac requeriría $\deg(v) \geq 23.5$ para todo
nodo, y el de Ore condiciones aún más fuertes. **Ninguno de estos teoremas
aplica a nuestro grafo**, donde el grado máximo observado ronda 9. Estos
teoremas son condiciones _suficientes pero no necesarias_: su incumplimiento no
implica que no exista un ciclo hamiltoniano, como de hecho demuestra la solución
encontrada.

#### 2.2.3 Condición Necesaria Verificada

Una **condición necesaria** (pero no suficiente) para la existencia de un ciclo
hamiltoniano es que $\deg(v) \geq 2$ para todo $v$. `solve_tsp.py` verifica esto
explícitamente:

```python
degree = defaultdict(int)
for u, v in edges:
    degree[u] += 1

for node in nodes:
    if degree[node] < 2:
        print(f"¡Atención! El nodo {node} tiene solo {degree[node]} conexiones.")
        impossible = True
```

Si algún nodo tuviera grado 1, sería imposible entrar y salir de él en un
recorrido cíclico, lo que haría el problema **infactible** por construcción.
Esta verificación proporciona un diagnóstico rápido antes de invocar el solver.

### 2.3 Distancias como Pesos

Los pesos de las aristas representan **distancias reales por carretera** en
kilómetros, no distancias euclidianas en línea recta. Esto es importante porque:

1. Las distancias no satisfacen la **desigualdad triangular** necesariamente (la
   carretera entre A y C podría ser más larga que A → B → C).
2. No es posible usar heurísticas geométricas (como el algoritmo de Christofides
   para el TSP métrico).
3. Los pesos capturan la topografía real del terreno y la infraestructura viaria
   española.

### 2.4 Grafo Real vs. Grafo Teórico

| Propiedad                     | Grafo Completo (teórico)                    | `network.txt` (real)                                            |
| ----------------------------- | ------------------------------------------- | --------------------------------------------------------------- |
| Número de nodos $n$           | 47                                          | 47                                                              |
| Número de aristas             | $\binom{47}{2} = 1081$                      | $\approx 110$ (únicas)                                          |
| Dirección                     | Bidireccional implícito                     | 2 × 110 = 220 aristas dirigidas (redondeado a 219 por cabecera) |
| Grado mínimo                  | 46                                          | 2 (crítico)                                                     |
| Grado máximo                  | 46                                          | 9                                                               |
| Grado promedio                | 46                                          | $\approx 219/47 \approx 4.66$                                   |
| Densidad                      | 100%                                        | $\approx$ 10.2%                                                 |
| Ciclos hamiltonianos teóricos | $\frac{46!}{2} \approx 2.75 \times 10^{57}$ | Muchos menos                                                    |

---

## 3. Programación Lineal Entera (ILP)

### 3.1 ¿Qué es la Programación Lineal Entera?

La **Programación Lineal Entera** (_Integer Linear Programming_, ILP) es una
técnica de optimización matemática donde:

1. Se define una **función objetivo lineal** a minimizar (o maximizar).
2. Se establecen **restricciones lineales** (ecuaciones o desigualdades).
3. Algunas (o todas) las variables de decisión están restringidas a valores
   **enteros**.

La forma canónica es:

$$\begin{aligned} \min \quad & \mathbf{c}^T \mathbf{x} \\ \text{sujeto a} \quad
& A\mathbf{x} \leq \mathbf{b} \\ & \mathbf{x} \in \mathbb{Z}^k \times
\mathbb{R}^{n-k} \end{aligned}$$

Un caso especial es la **Programación Lineal Binaria** (_Binary Integer
Programming_, BIP), donde las variables solo pueden tomar valores 0 o 1:

$$x_i \in \{0, 1\}$$

Esta es precisamente la naturaleza del TSP: cada decisión "viajar de i a j" es
binaria (sí/no).

### 3.2 Por qué ILP para el TSP

El TSP se presta naturalmente a una formulación ILP porque:

- Las decisiones son discretas y binarias (se toma o no se toma cada arista).
- La función objetivo (distancia total) es una combinación lineal de estas
  decisiones.
- Las restricciones (grado de entrada/salida, eliminación de subtours) son
  lineales.
- Existen solvers comerciales y libres (CPLEX, Gurobi, CBC) que pueden resolver
  problemas ILP de tamaño moderado en tiempos razonables usando técnicas
  avanzadas de _Branch and Cut_.

El ILP encuentra **la solución exacta óptima global**, no una aproximación
heurística. Para 47 nodos con un grafo disperso, el espacio de búsqueda se
reduce drásticamente y CBC puede resolverlo en segundos.

### 3.3 Variables de Decisión

#### 3.3.1 Variables Binarias $x_{ij}$

Para cada arista dirigida $(i, j)$ presente en `network.txt`, se define una
variable binaria:

$$x_{ij} = \begin{cases} 1 & \text{si el viajante va de la ciudad } i \text{ a
la ciudad } j \\ 0 & \text{en caso contrario} \end{cases}$$

En código:

```python
x = pulp.LpVariable.dicts("x", edges.keys(), cat=pulp.LpBinary)
```

El dominio de $x$ no cubre todos los pares posibles de ciudades ($47 \times 46 =
2162$ pares ordenados), solo aquellos que tienen una carretera directa en
`network.txt` ($219$ variables $x_{ij}$). Esto reduce **drásticamente** el
número de variables: de $2162$ a $219$, aproximadamente un **90% menos**.

#### 3.3.2 Variables Continuas $u_i$

Se introducen $n$ variables continuas de ordenación $u_i$, una por nodo:

$$u_i \in \mathbb{R}, \quad i \in V$$

Estas variables son la clave de la formulación MTZ para eliminar subtours (§4).
Aunque son continuas, la estructura del problema fuerza que tomen valores
enteros en la solución óptima (por la naturaleza de las restricciones MTZ).

```python
u_var = pulp.LpVariable.dicts("u", nodes, cat=pulp.LpContinuous)
```

### 3.4 Función Objetivo

El objetivo es minimizar la **distancia total recorrida**:

$$\min \sum_{(i,j) \in E} w_{ij} \cdot x_{ij}$$

Donde $w_{ij}$ es la distancia en kilómetros del tramo $i \to j$ (almacenada en
el diccionario `edges`). En código:

```python
prob += pulp.lpSum(edges[e] * x[e] for e in edges), "Total_Distance"
```

Por ejemplo, si la solución óptima toma las aristas $(M, TO)$, $(TO, CR)$, ...,
$(GU, M)$, la suma de sus distancias nos da el valor de la función objetivo
(~6036.3 km).

### 3.5 Restricciones de Grado

Cada ciudad debe tener **exactamente una arista de entrada** y **exactamente una
arista de salida** en el ciclo hamiltoniano:

$$\forall i \in V: \sum_{j \in V: (i,j)\in E} x_{ij} = 1 \quad \text{(una
salida)}$$

$$\forall i \in V: \sum_{j \in V: (j,i)\in E} x_{ji} = 1 \quad \text{(una
entrada)}$$

```python
for i in nodes:
    prob += pulp.lpSum(x[(i, j)] for j in nodes if (i, j) in edges) == 1, f"Out_{i}"
    prob += pulp.lpSum(x[(j, i)] for j in nodes if (j, i) in edges) == 1, f"In_{i}"
```

Estas $2n = 94$ restricciones son necesarias pero **no suficientes**. Garantizan
que cada nodo tenga grado 2 en la solución (el grado de un ciclo), pero no
impiden que la solución se fragmente en múltiples ciclos desconectados
(subtours). Por ejemplo, una solución factible bajo estas restricciones podría
ser:

- Ciclo 1: `M → TO → CR → M`
- Ciclo 2: `B → T → L → B`
- ...

Cada nodo aparece en exactamente un ciclo (grado 2), pero no se visita _todo_ en
un único recorrido. Este es el problema de los subtours.

---

## 4. Formulación MTZ (Miller-Tucker-Zemlin)

### 4.1 El Problema de los Subtours

Imaginemos 4 ciudades {A, B, C, D} formando un cuadrado. Con solo las
restricciones de grado, el solver podría proponer como solución:

- Subtour 1: `A → B → A`
- Subtour 2: `C → D → C`

Ambos ciclos satisfacen grado de entrada = grado de salida = 1 para cada nodo.
La distancia total podría ser baja, pero **no es un ciclo hamiltoniano** porque
no conecta todos los nodos en un único recorrido.

El desafío es añadir restricciones que **prohíban los subtours** sin enumerarlos
todos (lo cual sería exponencial: $2^{n}$ subconjuntos posibles).

### 4.2 Idea Central de MTZ

La formulación **Miller-Tucker-Zemlin** (1960) asigna a cada ciudad una variable
$u_i$ que representa el **orden de visita** en el recorrido:

$$u_i = \text{posición de la ciudad } i \text{ en la secuencia del viaje}$$

La ciudad de inicio (Madrid, `M`) se fija como la posición 1:

$$u_M = 1$$

Para todas las demás ciudades:

$$2 \leq u_i \leq n, \quad \forall i \neq M$$

La restricción clave de MTZ es:

$$\forall i,j \neq M, i \neq j, (i,j) \in E: \quad u_i - u_j + n \cdot x_{ij}
\leq n - 1$$

### 4.3 Demostración de que MTZ Elimina Subtours

#### Caso 1: $x_{ij} = 0$ (no se viaja de $i$ a $j$)

La restricción se reduce a:

$$u_i - u_j \leq n - 1$$

Como $2 \leq u_i, u_j \leq n$, la diferencia máxima posible es $n - 2$ (cuando
$u_i = n$ y $u_j = 2$). Por tanto $u_i - u_j \leq n - 2 < n - 1$, y la
restricción se satisface trivialmente. No impone ninguna limitación.

#### Caso 2: $x_{ij} = 1$ (se viaja de $i$ a $j$)

La restricción se convierte en:

$$u_i - u_j + n \leq n - 1$$

Despejando:

$$u_i - u_j \leq -1 \;\Longrightarrow\; u_j \geq u_i + 1$$

Esto significa que si viajamos de $i$ a $j$, la posición de $j$ en la secuencia
debe ser **estrictamente mayor** que la de $i$. El orden es monótono creciente a
lo largo de la ruta.

#### Por qué esto impide los subtours

Supongamos un subtour de $k$ nodos que no incluye a $M$: $v_1 \to v_2 \to \cdots
\to v_k \to v_1$. Aplicando MTZ a cada arista del subtour ($x_{v_1 v_2} = 1,
x_{v_2 v_3} = 1, \dots, x_{v_k v_1} = 1$):

$$\begin{aligned} u_{v_2} &\geq u_{v_1} + 1 \\ u_{v_3} &\geq u_{v_2} + 1 \geq
u_{v_1} + 2 \\ &\vdots \\ u_{v_k} &\geq u_{v_1} + (k-1) \\ u_{v_1} &\geq
u_{v_k} + 1 \geq u_{v_1} + k \end{aligned}$$

La última línea implica $u_{v_1} \geq u_{v_1} + k$, una **contradicción** puesto
que $k \geq 2$. Ergo, no puede existir un subtour que no pase por $M$. Como $M$
tiene $u_M = 1$ y está en la ruta principal, todos los nodos deben estar
encadenados desde $M$ en una única secuencia creciente de posiciones, formando
el ciclo hamiltoniano deseado.

### 4.4 Implementación en Código

```python
start_node = 'M'

# Rango de u_i
for i in nodes:
    if i == start_node:
        prob += u_var[i] == 1, f"MTZ_Init_{i}"
    else:
        prob += u_var[i] >= 2, f"MTZ_Min_{i}"
        prob += u_var[i] <= N, f"MTZ_Max_{i}"

# Restricción MTZ
for i in nodes:
    for j in nodes:
        if i != j and i != start_node and j != start_node and (i, j) in edges:
            prob += u_var[i] - u_var[j] + N * x[(i, j)] <= N - 1, \
                     f"MTZ_Subtour_{i}_{j}"
```

Detalles relevantes:

- **$M$ nunca aparece como destino en las restricciones MTZ**: Esto es correcto
  porque $M$ es el inicio y final, y la desigualdad ya no se sostiene para el
  último salto de vuelta a $M$ (porque $u_M = 1$ y el último nodo $i$ tiene $u_i
  = n$, así que $u_i - u_M = n-1$, y con $x_{iM} = 1$ la restricción daría
  $n-1 + n \leq n-1$, que es falso). El modelo lo maneja porque $M$ simplemente
  no aparece como $j$ en estas restricciones.

- **$M$ tampoco aparece como $i$**: Por la misma razón: de $M$ partimos y las
  restricciones de grado aseguran que $M$ tiene una arista de salida, pero no
  necesitamos forzar el orden desde $M$ con MTZ.

- **Número de restricciones MTZ**: Para $n = 47$ nodos, las restricciones MTZ se
  generan para cada par $(i, j)$ donde $i,j \neq M$, $i \neq j$, y existe la
  arista $(i, j)$ en `network.txt`. Esto produce un número de restricciones del
  orden de $O(n^2)$ en el peor caso para un grafo completo, pero en nuestro caso
  es sustancialmente menor por ser un grafo disperso.

### 4.5 Análisis de la Eficiencia de MTZ

| Formulación                         | N.º de variables  | N.º de restricciones              | Eliminación de subtours             |
| ----------------------------------- | ----------------- | --------------------------------- | ----------------------------------- |
| **MTZ**                             | $O(n^2) + O(n)$   | $O(n^2)$ restricciones explícitas | Implícita mediante variables $u_i$  |
| **DFJ** (Dantzig-Fulkerson-Johnson) | $O(n^2)$          | $O(2^n)$ (todas las posibles)     | Explícita: prohíbe cada subconjunto |
| **GG** (Gavish-Graves)              | $O(n^2) + O(n^2)$ | $O(n^2)$                          | Variables de flujo multi-commodity  |

**MTZ** fue elegida por su simplicidad de implementación y porque para $n = 47$
con un grafo disperso, la relajación lineal (el problema LP que resulta de
ignorar la integralidad de $x_{ij}$) es lo suficientemente fuerte como para que
el Branch & Bound converja rápido. Su principal desventaja teórica —que la
relajación LP es débil (produce cotas inferiores poco ajustadas)— no es crítica
a esta escala.

Para problemas de mayor tamaño ($n > 200$), formulaciones como **DFJ con lazy
constraints** (añadir restricciones de subtour solo cuando se detectan en la
solución, iterativamente) o **GG** ofrecerían mejor rendimiento.

### 4.6 Variantes de MTZ

La literatura ha propuesto mejoras a la formulación MTZ original:

- **MTZ reforzado** (Desrochers y Laporte, 1991): $u_i - u_j + n \cdot x_{ij} +
  (n-2) \cdot x_{ji} \leq n - 1$
- **MTZ apretado** (Sherali y Driscoll, 2002): $u_i - u_j + n\cdot x_{ij} +
  \alpha_{ij} \cdot x_{ji} \leq n - 1$ con $\alpha$ adaptativo.

Para nuestro caso, la formulación clásica es suficiente.

---

## 5. El Solver: PuLP + CBC

### 5.1 Arquitectura de PuLP

**PuLP** es una librería Python de modelado algebraico para problemas de
optimización lineal. Su arquitectura sigue el patrón de separación entre
**modelado** y **resolución**:

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Modelo PuLP │────▶│  Traductor  │────▶│  CBC Solver  │
│  (Python)    │     │  a LP/MPS   │     │  (C++ nativo)│
└──────────────┘     └─────────────┘     └──────────────┘
                                                │
                                          ┌─────▼──────┐
                                          │  Solución  │
                                          │  (valores  │
                                          │  óptimos)  │
                                          └────────────┘
```

1. **Fase de modelado**: Se construye un objeto `LpProblem`, se añaden variables
   (`LpVariable`), restricciones y la función objetivo usando la API declarativa
   de PuLP.
2. **Fase de resolución**: PuLP traduce el modelo a un archivo `.lp` o `.mps`
   (formatos estándar de la industria) y lo envía al solver externo CBC a través
   de una interfaz de línea de comandos.
3. **Fase de resultados**: PuLP parsea la salida del solver y la mapea de vuelta
   a las variables Python.

El método `prob.solve()` desencadena todo este proceso:

```python
prob.solve(pulp.PULP_CBC_CMD(msg=0))  # msg=0 suprime el log del solver
```

### 5.2 CBC (COIN-OR Branch and Cut)

**CBC** (_COIN-OR Branch and Cut_) es un solver de programación lineal
entera-mixta (MILP) de código abierto desarrollado por la iniciativa COIN-OR. Es
el solver por defecto de PuLP y se distribuye empaquetado con la librería.

#### 5.2.1 Algoritmo General: Branch and Cut

CBC combina tres técnicas fundamentales:

```
┌──────────────────────────────────────┐
│          BRANCH AND CUT              │
│                                      │
│  ┌───────────────┐                   │
│  │ Branch & Bound│◀──┐               │
│  │ (árbol de     │   │               │
│  │  búsqueda)    │   │               │
│  └───────┬───────┘   │               │
│          │           │               │
│          ▼           │               │
│  ┌───────────────┐   │               │
│  │  Relajación LP│   │               │
│  │  (Simplex /   │   │               │
│  │   Barrera)    │   │               │
│  └───────┬───────┘   │               │
│          │           │               │
│          ▼           │               │
│  ┌───────────────┐   │               │
│  │ Cutting Planes├───┘               │
│  │ (Gomory, etc.)│                   │
│  └───────────────┘                   │
│          │                           │
│          ▼                           │
│  ┌───────────────┐                   │
│  │ Heurísticas   │                   │
│  │ Primales      │                   │
│  └───────────────┘                   │
│                                      │
└──────────────────────────────────────┘
```

#### 5.2.2 Branch and Bound

El método de **ramificación y acotación** (_Branch and Bound_) explora el
espacio de soluciones construyendo un árbol de decisión:

1. **Raíz**: Se resuelve la **relajación LP** del problema (ignorando las
   restricciones de integralidad, permitiendo $0 \leq x_{ij} \leq 1$). Esto da
   una **cota inferior** (_lower bound_) de la solución óptima entera.
2. **Ramificación** (_branch_): Si alguna variable $x_{ij}$ tiene valor
   fraccionario (p.ej. 0.7), se crean dos subproblemas:
   - Subproblema 1: $x_{ij} = 0$
   - Subproblema 2: $x_{ij} = 1$
3. **Acotación** (_bound_): Se resuelve la relajación LP de cada subproblema. Si
   su cota inferior es peor que la mejor solución entera encontrada hasta ahora
   (la **cota superior** o _incumbent_), esa rama se descarta (_pruning_).
4. **Repetir** recursivamente hasta encontrar la solución óptima entera o
   demostrar optimalidad.

#### 5.2.3 Relajación LP y el Algoritmo Simplex

La **relajación LP** consiste en reemplazar $x_{ij} \in \{0, 1\}$ por $0 \leq
x_{ij} \leq 1$. El problema resultante es un **Programa Lineal** (LP) que puede
resolverse eficientemente con el **algoritmo Simplex** (Dantzig, 1947) o métodos
de **punto interior** (barrera).

- **Simplex primal**: Recorre vértices adyacentes del politopo definido por las
  restricciones, mejorando la función objetivo en cada paso, hasta alcanzar el
  óptimo.
- **Complejidad**: En el peor caso, el Simplex es exponencial (poliedro de
  Klee-Minty), pero en la práctica su complejidad es $O(n^3)$ aproximada y es
  excepcionalmente rápido para problemas de este tamaño.

#### 5.2.4 Cutting Planes (Planos de Corte)

Los **planos de corte** añaden restricciones redundantes (desde el punto de
vista entero) que "recortan" la región factible de la relajación LP, acercándola
a la envolvente convexa de las soluciones enteras.

- **Cortes de Gomory**: Derivados de la tabla Simplex. Si en la solución LP
  óptima una variable entera $x_k$ toma valor fraccionario, se genera un corte
  que elimina esa solución fraccionaria sin eliminar ninguna solución entera.
- **Cortes de clique, cobertura, etc.**: Explotan la estructura combinatoria
  específica del problema.

CBC aplica cortes automáticamente en cada nodo del árbol. Para el TSP con MTZ,
los cortes más efectivos suelen ser los de Gomory, que refuerzan la relajación y
reducen el número de nodos del árbol.

#### 5.2.5 Heurísticas Primales

Además de la búsqueda exacta, CBC emplea **heurísticas primales** para encontrar
rápidamente buenas soluciones enteras (cotas superiores):

- **Redondeo**: A partir de la solución LP fraccionaria, redondear variables a
  0/1 y verificar factibilidad.
- **Búsqueda local**: Pequeñas perturbaciones sobre soluciones factibles para
  mejorarlas.
- **Feasibility Pump**: Alterna entre satisfacer restricciones e integralidad.

Estas heurísticas ayudan a encontrar un buen _incumbent_ temprano, permitiendo
podar más ramas del árbol.

#### 5.2.6 Por qué `msg=0`

El parámetro `msg=0` suprime el log de CBC. Durante el desarrollo puede ser útil
verlo (con `msg=1`) para entender la convergencia:

```
Cbc0012I Integer solution of 6500 found by heuristic
Cbc0038I Full problem 0 rows 0 columns 0 non zeros
Cbc0038I Optimal - objective value 6036.3
```

Pero en el script final se oculta para limpiar la salida.

### 5.3 Procesamiento de Resultados

Tras la llamada a `prob.solve()`, el estado se inspecciona:

```python
if prob.status == pulp.LpStatusOptimal:
    # Solución óptima encontrada
    distancia = pulp.value(prob.objective)
elif prob.status == pulp.LpStatusInfeasible:
    # Ninguna solución existe
    print("INFACTIBLE")
else:
    # Otro estado (no acotado, timeout, etc.)
    print(prob.status)
```

#### Reconstrucción de la Ruta

Los valores de las variables $x_{ij}$ se leen para reconstruir la secuencia de
ciudades:

```python
next_node = {}
for (i, j) in edges:
    if pulp.value(x[(i, j)]) and pulp.value(x[(i, j)]) > 0.5:
        next_node[i] = j

path = [start_node]
current = start_node
while True:
    current = next_node[current]
    path.append(current)
    if current == start_node:
        break
```

El umbral `> 0.5` es una buena práctica: debido a errores de precisión numérica
del solver, una variable binaria podría valer 0.9999999 o 1.0000001 en lugar de
exactamente 1.0.

---

## 6. Técnicas de Visualización

### 6.1 Visualización de Grafos con NetworkX + Matplotlib

#### 6.1.1 Construcción del Grafo

`draw_route.py` construye un `nx.Graph()` no dirigido a partir de `network.txt`:

```python
G = nx.Graph()
G.add_edge(u, v, weight=w)
```

NetworkX deduplica automáticamente las aristas M→AV y AV→M (son la misma arista
no dirigida), generando un grafo con aproximadamente 110 aristas.

#### 6.1.2 Algoritmo de Layout: Kamada-Kawai

El layout **Kamada-Kawai** (1989) es un algoritmo de disposición de nodos basado
en fuerzas, diseñado específicamente para grafos ponderados. Pertenece a la
familia de algoritmos _force-directed_.

**Principio**: Busca una disposición de los nodos en el plano donde las
distancias euclidianas entre nodos sean proporcionales a las distancias del
camino más corto (_shortest path_) en el grafo:

$$E = \sum_{i=1}^{n-1}\sum_{j=i+1}^{n} \frac{1}{2}k_{ij}(|p_i - p_j| -
d_{ij})^2$$

Donde:

- $p_i$ es la posición 2D del nodo $i$ (a optimizar).
- $d_{ij}$ es la distancia del camino más corto entre $i$ y $j$ en el grafo
  (calculada con el algoritmo de Dijkstra).
- $k_{ij} = K / d_{ij}^2$ es la constante de resorte (más fuerza para nodos
  cercanos).

La función de energía $E$ se minimiza iterativamente usando una variante del
método de Newton-Raphson por pares de nodos.

**Ventajas para este proyecto**:

- Captura la estructura global del grafo: nodos geográficamente cercanos tienden
  a aparecer juntos.
- Evita el solapamiento de nodos.
- No requiere coordenadas geográficas iniciales.
- Produce visualizaciones estéticamente agradables de grafos de tamaño medio
  (∼50 nodos).

**Desventajas**:

- Complejidad $O(n^3)$ para calcular todas las distancias entre pares y $O(n^2)$
  por iteración de optimización.
- El mínimo encontrado es un mínimo local, no necesariamente global.
- La orientación es arbitraria (el mapa puede aparecer rotado respecto al norte
  geográfico real).

```python
pos = nx.kamada_kawai_layout(G, weight="weight")
```

#### 6.1.3 Elementos Visuales

| Elemento           | Renderizado                                                                             | Propósito                                       |
| ------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Nodos              | `nx.draw_networkx_nodes` — círculos azules claros `#87CEFA` con borde negro, tamaño 600 | Representar las 47 ciudades                     |
| Etiquetas          | `nx.draw_networkx_labels` — fuente negrita, tamaño 9                                    | Identificar cada ciudad por su código           |
| Aristas de la red  | `nx.draw_networkx_edges` — gris claro `#cccccc`, discontinuas, alfa 0.5                 | Mostrar todas las carreteras existentes (fondo) |
| Aristas de la ruta | `nx.draw_networkx_edges` — rojo `#e74c3c`, ancho 3.5, solo `path_edges`                 | Resaltar el ciclo hamiltoniano óptimo           |
| Nodo inicio        | `nx.draw_networkx_nodes` — amarillo dorado `#f1c40f`, tamaño 800, solo `['M']`          | Destacar Madrid como punto de partida           |

El archivo resultante es `ruta_optima.png` (14×10 pulgadas, 150 DPI, 2100×1500
píxeles).

### 6.2 Mapa Interactivo con Folium + Geopy

#### 6.2.1 Geocodificación con Nominatim

**Nominatim** es el geocodificador de OpenStreetMap (OSM). Convierte nombres de
lugares en coordenadas geográficas (latitud, longitud) mediante búsqueda textual
en la base de datos de OSM.

```python
geolocator = Nominatim(user_agent="viajante_spain_agent")
location = geolocator.geocode(f"{city_name}, Spain")
```

El parámetro `user_agent` es obligatorio: Nominatim bloquea peticiones sin un
User-Agent identificativo.

**Respeto de límites de uso**: La política de uso de Nominatim exige un máximo
de **1 petición por segundo**. El script implementa:

```python
time.sleep(1.2)  # 1.2 segundos entre peticiones
```

Esto significa que geocodificar las 47 ciudades tarda aproximadamente $47 \times
1.2 \approx 56$ segundos. Para evitar repetir este proceso, `draw_map.py` persiste
las coordenadas en `data/coordenadas.json`, y `draw_static_map.py` las lee
directamente de ese archivo.

#### 6.2.2 Folium

**Folium** es una librería Python que actúa como wrapper de **Leaflet.js**, la
biblioteca JavaScript de mapas interactivos más popular del ecosistema
open-source.

**Elementos del mapa**:

```python
m = folium.Map(location=[40.0, -4.0], zoom_start=6, tiles="cartodbpositron")
```

| Parámetro    | Valor               | Significado                                                  |
| ------------ | ------------------- | ------------------------------------------------------------ |
| `location`   | `[40.0, -4.0]`      | Centro del mapa: centro geográfico de la Península Ibérica   |
| `zoom_start` | `6`                 | Zoom inicial: permite ver toda España peninsular             |
| `tiles`      | `"cartodbpositron"` | Estilo visual de mapa: claro, minimalista, sin distracciones |

Los marcadores de ciudad se añaden con:

```python
folium.Marker(
    [lat, lon],
    popup=city_name,       # Se muestra al hacer clic
    tooltip=city_name,     # Se muestra al pasar el ratón
    icon=folium.Icon(color="red" if code == "M" else "blue")
).add_to(m)
```

La ruta se dibuja como una **polilínea** conectando las coordenadas en el orden
de visita:

```python
folium.PolyLine(
    route_coords,
    weight=4,        # Grosor de línea en píxeles
    color="red",     # Color distintivo
    opacity=0.8      # Ligera transparencia para no ocultar el mapa base
).add_to(m)
```

El resultado es un archivo HTML autocontenido (`mapa_ruta.html`) que puede
abrirse en cualquier navegador sin servidor web, con zoom, desplazamiento y
popups interactivos.

### 6.3 Mapa Estático con StaticMap

#### 6.3.1 Motivación

GitHub no permite incrustar HTML/JavaScript arbitrario en archivos Markdown por
razones de seguridad. Para mostrar la ruta en el `README.md`, se necesita una
imagen estática (PNG).

#### 6.3.2 StaticMap

**StaticMap** es una librería Python que genera imágenes rasterizadas combinando
tiles de OpenStreetMap:

```python
m = StaticMap(1200, 800)                       # Ancho × Alto en píxeles
image = m.render(zoom=6)                       # Nivel de zoom OSM
image.save('mapa_ruta_estatico.png')
```

**Coordenadas desde archivo**: Para evitar repetir la geocodificación (lenta),
las coordenadas generadas por `draw_map.py` se persisten en `data/coordenadas.json`
(formato JSON: `{"M": [40.416, -3.703], "TO": [39.855, -4.024], ...}`) y
`draw_static_map.py` las lee desde ahí.
```

**Convención de coordenadas**: Es importante notar la diferencia:

| Librería           | Orden de coordenadas |
| ------------------ | -------------------- |
| Folium, Geopy      | `(lat, lon)`         |
| StaticMap, Leaflet | `(lon, lat)`         |

El código maneja esta conversión explícitamente:

```python
route_lonlat = [(coords[code][1], coords[code][0]) for code in ruta]
```

**Elementos visuales**:

| Elemento | Clase                                   | Visualización                                                                            |
| -------- | --------------------------------------- | ---------------------------------------------------------------------------------------- |
| Ciudades | `CircleMarker((lon, lat), color, size)` | Círculos: rojo `#FF0000` para Madrid (tamaño 8), azul `#3366CC` para el resto (tamaño 6) |
| Ruta     | `Line(route_lonlat, 'red', 4)`          | Línea roja de grosor 4 píxeles conectando el recorrido                                   |

---

## 7. Análisis de Resultados

### 7.1 Ruta Óptima Encontrada

La solución exacta encontrada por el solver CBC es:

```
M → TO → CR → CC → BA → H → SE → CA → MA → CO →
J → GR → AL → MU → A → AB → CU → TE → V → CS →
T → B → GE → L → HU → Z → SO → LO → NA → SS →
VI → BI → S → BU → VA → P → LE → O → LU → C →
PO → OR → ZA → SA → AV → SG → GU → M
```

**Distancia total óptima**: **6.036,3 kilómetros**

**Número de tramos**: 47 (visita 47 ciudades y regresa a Madrid)

**Distancia media por tramo**: $6036.3 / 47 \approx 128.4$ km

### 7.2 Interpretación Geográfica

El recorrido sigue un patrón geográfico notable:

| Zona               | Ciudades visitadas consecutivamente                    |
| ------------------ | ------------------------------------------------------ |
| **Centro-Sur**     | M → TO → CR → CC → BA → H → SE → CA → MA → CO → J → GR |
| **Levante**        | AL → MU → A → AB → CU → TE → V → CS                    |
| **Cataluña**       | T → B → GE → L                                         |
| **Valle del Ebro** | HU → Z → SO → LO → NA                                  |
| **Cantábrico**     | SS → VI → BI → S → BU                                  |
| **Meseta Norte**   | VA → P → LE                                            |
| **Noroeste**       | O → LU → C → PO → OR                                   |
| **Oeste**          | ZA → SA → AV → SG → GU                                 |
| **Retorno**        | GU → M                                                 |

El orden optimiza naturalmente el recorrido siguiendo una espiral antihoraria
desde Madrid hacia el sur, remontando por la costa mediterránea, atravesando el
Pirineo, recorriendo la cornisa cantábrica de este a oeste, bajando por la
fachada atlántica y retornando por la meseta norte.

### 7.3 Tiempos de Viaje Estimados

Asumiendo una velocidad media de **85 km/h** (combinación de autovías y
carreteras nacionales):

| Escenario                            | Cálculo                                       | Tiempo             |
| ------------------------------------ | --------------------------------------------- | ------------------ |
| **Conducción pura**                  | $6036.3 / 85$                                 | $\approx 71$ horas |
| **Profesional (9h/día)**             | $71 / 9$                                      | $\approx 8$ días   |
| **Profesional + 1h parada/ciudad**   | $(71 + 47) / 9$                               | $\approx 13$ días  |
| **Turismo express (2 ciudades/día)** | $71 / 3$ horas/día                            | $\approx 24$ días  |
| **Turismo clásico (disfrute)**       | Con estancias de 2-3 días en grandes ciudades | $\approx 45$ días  |
| **Slow travel**                      | Sin prisas, explorando entorno                | $60+$ días         |

---

## 8. Apéndice A: Glosario de Ciudades

| Código | Ciudad                 | Código | Ciudad               |
| ------ | ---------------------- | ------ | -------------------- |
| A      | Alicante/Alacant       | AB     | Albacete             |
| AL     | Almería                | AV     | Ávila                |
| B      | Barcelona              | BA     | Badajoz              |
| BI     | Bilbao/Bilbo           | BU     | Burgos               |
| C      | A Coruña               | CA     | Cádiz                |
| CC     | Cáceres                | CO     | Córdoba              |
| CR     | Ciudad Real            | CS     | Castelló de la Plana |
| CU     | Cuenca                 | GE     | Girona               |
| GR     | Granada                | GU     | Guadalajara          |
| H      | Huelva                 | HU     | Huesca               |
| J      | Jaén                   | L      | Lleida               |
| LE     | León                   | LO     | Logroño              |
| LU     | Lugo                   | M      | Madrid               |
| MA     | Málaga                 | MU     | Murcia               |
| NA     | Pamplona/Iruña         | O      | Oviedo/Uviéu         |
| OR     | Ourense                | P      | Palencia             |
| PO     | Pontevedra             | S      | Santander            |
| SA     | Salamanca              | SE     | Sevilla              |
| SG     | Segovia                | SO     | Soria                |
| SS     | Donostia/San Sebastián | T      | Tarragona            |
| TE     | Teruel                 | TO     | Toledo               |
| V      | València               | VA     | Valladolid           |
| VI     | Vitoria-Gasteiz        | Z      | Zaragoza             |
| ZA     | Zamora                 |        |                      |

**Nota**: Ceuta (CE) y Melilla (ML), así como las capitales insulares (Palma de
Mallorca, Las Palmas de Gran Canaria, Santa Cruz de Tenerife), no están
incluidas en la red por carecer de conexiones terrestres con la península.

---

## 9. Apéndice B: Ejecución del Proyecto

### Requisitos

- Python $\geq$ 3.13
- `uv` (gestor de paquetes)
- `just` (orquestador de tareas)

### Instalación

```bash
uv sync
```

### Orquestador (recomendado)

```bash
just all        # Pipeline completo: conectar → resolver → grafo → mapa → estatico
just resolver   # Solo el solver TSP → data/ruta_optima.json
just grafo      # Solo el grafo → ruta_optima.png
just mapa       # Solo el mapa interactivo → mapa_ruta.html + data/coordenadas.json
just estatico   # Solo el mapa estático → mapa_ruta_estatico.png
just conectar   # Solo la conectividad → data/conectividad.json
just rutas      # Solo el cálculo teórico de rutas
just clean      # Limpiar todos los archivos generados
```

### Ejecución Manual

```bash
uv run python solve_tsp.py          # Solver TSP → data/ruta_optima.json
uv run python draw_route.py         # Grafo estático → ruta_optima.png
uv run python draw_map.py           # Mapa interactivo → mapa_ruta.html + data/coordenadas.json
uv run python draw_static_map.py    # Mapa estático → mapa_ruta_estatico.png
uv run python connectivity.py       # Distribución de grados → data/conectividad.json
uv run python tsp_routes_count.py   # Número teórico de rutas
```

### Salida esperada del solver

```
Total de ciudades en la red: 47
Resolviendo el modelo (esto puede tardar unos segundos dependiendo de la red)...

¡Solución óptima exacta encontrada!
Distancia total: 6036.30

Ruta óptima:
M -> TO -> CR -> CC -> BA -> H -> SE -> CA -> MA -> CO ->
J -> GR -> AL -> MU -> A -> AB -> CU -> TE -> V -> CS ->
T -> B -> GE -> L -> HU -> Z -> SO -> LO -> NA -> SS ->
VI -> BI -> S -> BU -> VA -> P -> LE -> O -> LU -> C ->
PO -> OR -> ZA -> SA -> AV -> SG -> GU -> M

Ruta guardada en data/ruta_optima.json
```

---

## Referencias

1. Dantzig, G., Fulkerson, R., Johnson, S. (1954). _Solution of a Large-Scale
   Traveling-Salesman Problem_. Journal of the Operations Research Society of
   America.
2. Miller, C. E., Tucker, A. W., Zemlin, R. A. (1960). _Integer Programming
   Formulation of Traveling Salesman Problems_. Journal of the ACM.
3. Karp, R. M. (1972). _Reducibility Among Combinatorial Problems_. Complexity
   of Computer Computations.
4. Kamada, T., Kawai, S. (1989). _An Algorithm for Drawing General Undirected
   Graphs_. Information Processing Letters.
5. Desrochers, M., Laporte, G. (1991). _Improvements and Extensions to the
   Miller-Tucker-Zemlin Subtour Elimination Constraints_. Operations Research
   Letters.
6. Applegate, D. L., Bixby, R. E., Chvátal, V., Cook, W. J. (2006). _The
   Traveling Salesman Problem: A Computational Study_. Princeton University
   Press.
7. COIN-OR Foundation. _CBC User Guide_. https://github.com/coin-or/Cbc
8. OpenStreetMap Contributors. _Nominatim Usage Policy_.
   https://operations.osmfoundation.org/policies/nominatim/
