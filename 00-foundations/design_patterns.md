# Software Design Patterns Reference

A working reference to the 23 classic Gang-of-Four design patterns, organized
by category. Each entry covers intent, the problem it solves, structure,
a minimal Java example, and when (and when not) to reach for it.

---

## Creational Patterns

Creational patterns abstract the instantiation process, decoupling a system
from how its objects are created, composed, and represented.

### Singleton

**Intent:** Ensure a class has exactly one instance, and provide a single
global access point to it.

**Problem:** Some components genuinely need exactly one instance — a
connection pool, a configuration registry, a logging facade. Allowing
multiple instances wastes resources at best, and causes subtle state
inconsistency bugs at worst (two connection pools each thinking they alone
own the database connections).

**Structure:** A private constructor prevents external instantiation. A
static field holds the single instance. A static accessor method creates the
instance lazily (or returns the existing one) and is the only way to reach it.

**Example:**

```java
public final class ConnectionPool {
    private static volatile ConnectionPool instance;
    private final List<Connection> connections = new ArrayList<>();

    private ConnectionPool() {
        // expensive setup happens exactly once
    }

    public static ConnectionPool getInstance() {
        if (instance == null) {
            synchronized (ConnectionPool.class) {
                if (instance == null) {
                    instance = new ConnectionPool();
                }
            }
        }
        return instance;
    }
}
```

**When to use:** Shared, expensive-to-construct resources with genuinely
global scope — a cache, a thread pool, a hardware interface.

**Trade-offs:** Singletons are a globally mutable state smell in disguise.
They make unit testing harder (you can't swap in a fake instance without
extra machinery), and they hide dependencies — a class that silently calls
`ConnectionPool.getInstance()` doesn't declare that dependency in its
constructor, so you can't see it from the outside. In frameworks like
Spring, prefer a singleton-scoped bean (the framework manages the lifecycle
and lets you inject a test double) over a hand-rolled Singleton class.

---

### Factory Method

**Intent:** Define an interface for creating an object, but let subclasses
decide which concrete class to instantiate.

**Problem:** A class can't anticipate which concrete subclass of a product
it needs to create, and wants to defer that decision to subclasses.

**Structure:** An abstract `Creator` declares a `factoryMethod()` returning
a `Product` interface. Concrete creators override it to return a specific
`ConcreteProduct`.

**Example:**

```java
abstract class NotificationService {
    abstract Notification createNotification(String content);

    void send(String content) {
        Notification n = createNotification(content);
        n.deliver();
    }
}

class EmailNotificationService extends NotificationService {
    @Override
    Notification createNotification(String content) {
        return new EmailNotification(content);
    }
}

class SmsNotificationService extends NotificationService {
    @Override
    Notification createNotification(String content) {
        return new SmsNotification(content);
    }
}
```

**When to use:** A class's code works entirely in terms of an abstract
product type, and you want subclasses to supply the concrete type without
changing the base algorithm (`send`, above).

**Trade-offs:** Requires subclassing just to change which product gets
created — can feel heavy for a simple variation. Often superseded in modern
code by passing in a factory function/lambda instead of a whole subclass.

---

### Abstract Factory

**Intent:** Provide an interface for creating families of related objects
without specifying their concrete classes.

**Problem:** A system needs to work with multiple families of related
products (e.g., UI components for Windows vs. macOS) and must stay agnostic
to which family is in use, while guaranteeing it never accidentally mixes
components from different families.

**Structure:** An `AbstractFactory` interface declares creation methods for
each product type in the family. Concrete factories (`WindowsFactory`,
`MacFactory`) implement all of them consistently.

**Example:**

```java
interface UIFactory {
    Button createButton();
    Checkbox createCheckbox();
}

class MacUIFactory implements UIFactory {
    public Button createButton() { return new MacButton(); }
    public Checkbox createCheckbox() { return new MacCheckbox(); }
}

class WindowsUIFactory implements UIFactory {
    public Button createButton() { return new WindowsButton(); }
    public Checkbox createCheckbox() { return new WindowsCheckbox(); }
}
```

**When to use:** Cross-platform UI toolkits, pluggable database drivers,
theme systems — anywhere you must swap an entire *family* of related
objects together, atomically.

**Trade-offs:** Adding a new product type means touching every concrete
factory. Overkill if you only ever have one family in practice.

---

### Builder

**Intent:** Separate the construction of a complex object from its
representation, so the same construction process can produce different
representations, and construction with many optional parameters stays
readable.

**Problem:** A constructor with ten parameters, half of them optional, is
unreadable and error-prone at the call site (which positional argument was
which, again?).

**Structure:** A `Builder` exposes chained setter-like methods, each
returning `this`, culminating in a `build()` call that assembles and
validates the final immutable object.

**Example:**

```java
public final class HttpRequest {
    private final String url;
    private final String method;
    private final Map<String, String> headers;

    private HttpRequest(Builder b) {
        this.url = b.url;
        this.method = b.method;
        this.headers = b.headers;
    }

    public static class Builder {
        private String url;
        private String method = "GET";
        private Map<String, String> headers = new HashMap<>();

        public Builder url(String url) { this.url = url; return this; }
        public Builder method(String m) { this.method = m; return this; }
        public Builder header(String k, String v) { headers.put(k, v); return this; }

        public HttpRequest build() {
            if (url == null) throw new IllegalStateException("url is required");
            return new HttpRequest(this);
        }
    }
}

HttpRequest req = new HttpRequest.Builder()
    .url("https://api.example.com")
    .method("POST")
    .header("Content-Type", "application/json")
    .build();
```

**When to use:** Objects with many optional fields, objects that need
validation at construction time, or objects that should be immutable once
built.

**Trade-offs:** More boilerplate than a plain constructor for simple cases.
Lombok's `@Builder` generates this exact pattern automatically in Java,
which is why you rarely hand-write it today.

---

### Prototype

**Intent:** Specify the kinds of objects to create using a prototypical
instance, and create new objects by copying this prototype.

**Problem:** Creating an object from scratch is expensive (e.g., it requires
a database round-trip to populate), but you already have a similar,
fully-populated instance sitting around that you'd like to clone and tweak.

**Structure:** Objects implement a `clone()` method (or copy constructor)
that returns a new instance with the same state, which the caller then
mutates independently.

**Example:**

```java
class GameCharacter implements Cloneable {
    String type;
    int level;
    List<String> inventory;

    @Override
    public GameCharacter clone() {
        GameCharacter copy = new GameCharacter();
        copy.type = this.type;
        copy.level = this.level;
        copy.inventory = new ArrayList<>(this.inventory); // deep copy!
        return copy;
    }
}
```

**When to use:** Spawning many similar objects from a template (game
enemies, document templates) where the setup cost of each is nontrivial.

**Trade-offs:** Easy to accidentally do a shallow copy and share mutable
nested state between the "copies," causing bugs that are hard to trace.
Always double check whether a field needs a deep copy.

---

## Structural Patterns

Structural patterns are concerned with how classes and objects are composed
to form larger structures, while keeping those structures flexible and
efficient.

### Adapter

**Intent:** Convert the interface of a class into another interface clients
expect, letting classes work together that couldn't otherwise because of
incompatible interfaces.

**Problem:** You have an existing class (often third-party, unmodifiable)
whose interface doesn't match what your code expects to call.

**Structure:** An `Adapter` implements the target interface and wraps an
instance of the incompatible class, translating calls between the two.

**Example:**

```java
interface PaymentProcessor {
    void charge(double amountUsd);
}

// Third-party library we can't modify
class LegacyBillingSystem {
    void billInCents(long cents) { /* ... */ }
}

class LegacyBillingAdapter implements PaymentProcessor {
    private final LegacyBillingSystem legacy;

    LegacyBillingAdapter(LegacyBillingSystem legacy) { this.legacy = legacy; }

    @Override
    public void charge(double amountUsd) {
        legacy.billInCents(Math.round(amountUsd * 100));
    }
}
```

**When to use:** Integrating a third-party or legacy API into a codebase
built around a different interface, without modifying either side.

**Trade-offs:** Adds a layer of indirection; a thin wrapper class per
integration. Usually worth it for the decoupling it buys.

---

### Bridge

**Intent:** Decouple an abstraction from its implementation so the two can
vary independently.

**Problem:** A class hierarchy has two dimensions of variation (e.g., shape
type AND rendering API), and subclassing for every combination causes a
combinatorial explosion of classes.

**Structure:** An `Abstraction` holds a reference to an `Implementor`
interface rather than inheriting from a concrete implementation, so either
side can be swapped or extended independently.

**Example:**

```java
interface Renderer {
    void renderCircle(float radius);
}

class VectorRenderer implements Renderer {
    public void renderCircle(float radius) { /* draw as vector */ }
}

class RasterRenderer implements Renderer {
    public void renderCircle(float radius) { /* draw as pixels */ }
}

abstract class Shape {
    protected Renderer renderer;
    Shape(Renderer renderer) { this.renderer = renderer; }
    abstract void draw();
}

class Circle extends Shape {
    float radius;
    Circle(Renderer renderer, float radius) {
        super(renderer);
        this.radius = radius;
    }
    void draw() { renderer.renderCircle(radius); }
}
```

**When to use:** Two independently-varying dimensions (shape × renderer,
device × driver) where subclassing per combination would be unmanageable.

**Trade-offs:** More upfront design complexity than a simple hierarchy;
only pays off once you actually have (or anticipate) that second dimension.

---

### Composite

**Intent:** Compose objects into tree structures and let clients treat
individual objects and compositions of objects uniformly.

**Problem:** A UI (or file system, or org chart) has both leaf elements and
containers of elements, and client code shouldn't need to special-case
"is this a single thing or a group of things."

**Structure:** A common `Component` interface is implemented by both `Leaf`
and `Composite` (which holds a list of child `Component`s and delegates
operations to them recursively).

**Example:**

```java
interface FileSystemNode {
    long size();
}

class File implements FileSystemNode {
    long sizeBytes;
    public long size() { return sizeBytes; }
}

class Directory implements FileSystemNode {
    List<FileSystemNode> children = new ArrayList<>();
    public long size() {
        return children.stream().mapToLong(FileSystemNode::size).sum();
    }
}
```

**When to use:** Any genuine tree structure — file systems, UI widget
trees, org charts, nested menus — where operations should apply uniformly
at any level.

**Trade-offs:** Can make it awkward to restrict certain operations to only
leaves or only composites, since both implement the same interface.

---

### Decorator

**Intent:** Attach additional responsibilities to an object dynamically,
providing a flexible alternative to subclassing for extending behavior.

**Problem:** You want to add behavior to individual objects, in flexible
combinations, without creating a subclass for every possible combination of
added behaviors.

**Structure:** A `Decorator` implements the same interface as the object it
wraps, holds a reference to the wrapped object, and adds behavior before or
after delegating the call.

**Example:**

```java
interface Coffee {
    double cost();
}

class SimpleCoffee implements Coffee {
    public double cost() { return 2.0; }
}

abstract class CoffeeDecorator implements Coffee {
    protected final Coffee wrapped;
    CoffeeDecorator(Coffee wrapped) { this.wrapped = wrapped; }
}

class WithMilk extends CoffeeDecorator {
    WithMilk(Coffee wrapped) { super(wrapped); }
    public double cost() { return wrapped.cost() + 0.5; }
}

class WithCaramel extends CoffeeDecorator {
    WithCaramel(Coffee wrapped) { super(wrapped); }
    public double cost() { return wrapped.cost() + 0.7; }
}

Coffee order = new WithCaramel(new WithMilk(new SimpleCoffee()));
System.out.println(order.cost()); // 3.2
```

**When to use:** Java's own `InputStream`/`BufferedInputStream`/
`GZIPInputStream` chain is the canonical real-world example — stackable,
independent behaviors layered onto a common interface.

**Trade-offs:** Deeply nested decorators are hard to read and debug; the
stack trace through many wrapped `cost()` calls can be confusing.

---

### Facade

**Intent:** Provide a unified, simplified interface to a set of interfaces
in a subsystem, making the subsystem easier to use.

**Problem:** A subsystem (e.g., video encoding, with a dozen fiddly
sub-components) is powerful but has a complicated, chatty API that most
callers shouldn't need to understand.

**Structure:** A `Facade` class exposes a small number of high-level
methods, internally coordinating calls across many subsystem classes.

**Example:**

```java
class VideoFacade {
    private final Codec codec = new Codec();
    private final AudioMixer mixer = new AudioMixer();
    private final FileWriter writer = new FileWriter();

    void convertToMp4(String inputPath, String outputPath) {
        var decoded = codec.decode(inputPath);
        var mixed = mixer.normalize(decoded.audioTrack());
        var encoded = codec.encodeMp4(decoded.videoTrack(), mixed);
        writer.save(encoded, outputPath);
    }
}
```

**When to use:** Nearly every well-designed service layer in a Spring Boot
app is a facade over repositories, external clients, and business logic —
this is one of the most commonly (if unconsciously) applied patterns.

**Trade-offs:** If overused, the facade becomes a god-object that knows
too much about the subsystem — keep it thin and delegate real logic down.

---

### Flyweight

**Intent:** Use sharing to support large numbers of fine-grained objects
efficiently, by factoring out and sharing state common across many objects.

**Problem:** You need millions of similar objects (e.g., characters in a
text editor, trees in a forest-rendering engine), and storing every piece of
state (font, color, glyph bitmap) per-instance would exhaust memory.

**Structure:** Shared, immutable state ("intrinsic") is factored into a
Flyweight stored once in a factory/cache; unique, per-instance state
("extrinsic," e.g. position) is passed in by the caller at use time.

**Example:**

```java
class TreeType { // intrinsic/shared state: heavy
    String name;
    byte[] meshData;
    byte[] textureData;
}

class TreeTypeFactory {
    private static final Map<String, TreeType> cache = new HashMap<>();
    static TreeType get(String name) {
        return cache.computeIfAbsent(name, n -> loadFromDisk(n));
    }
}

class Tree { // extrinsic state: light, per-instance
    int x, y;
    TreeType type; // shared reference, not a copy
}
```

**When to use:** Massive counts of objects that share most of their heavy
state — glyphs, particles, game-world entities of the same type.

**Trade-offs:** Adds real complexity to separate intrinsic from extrinsic
state correctly; only worth it once you've actually measured a memory
problem.

---

### Proxy

**Intent:** Provide a surrogate or placeholder for another object to control
access to it.

**Problem:** You need to add a layer of control around access to an
object — lazy loading, access checks, caching, logging — without changing
the object's own code or its callers.

**Structure:** A `Proxy` implements the same interface as the real object,
holds a reference to it (often created lazily), and adds its own logic
around delegating calls.

**Example:**

```java
interface Image {
    void display();
}

class RealImage implements Image {
    private final String path;
    RealImage(String path) {
        this.path = path;
        loadFromDisk(path); // expensive
    }
    public void display() { /* render it */ }
}

class LazyImageProxy implements Image {
    private final String path;
    private RealImage real;

    LazyImageProxy(String path) { this.path = path; }

    public void display() {
        if (real == null) {
            real = new RealImage(path); // deferred until actually needed
        }
        real.display();
    }
}
```

**When to use:** Lazy initialization, access control, remote object stubs
(this is exactly what RPC/gRPC client stubs are), and caching proxies.
Spring's `@Transactional` and `@Cacheable` work by generating a dynamic
proxy around your bean at runtime.

**Trade-offs:** An extra layer of indirection to reason about; dynamic
proxies (as Spring uses) can make stack traces harder to read.

---

## Behavioral Patterns

Behavioral patterns are concerned with algorithms and the assignment of
responsibilities between objects — how objects interact and distribute work.

### Chain of Responsibility

**Intent:** Avoid coupling the sender of a request to its receiver by giving
more than one object a chance to handle the request, chained in sequence.

**Problem:** A request might need to be handled by one of several possible
handlers, and you don't want the caller to know which one in advance, or to
hard-code the decision logic.

**Structure:** Each `Handler` holds a reference to the next handler in the
chain; it either handles the request or passes it along.

**Example:**

```java
abstract class SupportHandler {
    protected SupportHandler next;
    SupportHandler setNext(SupportHandler next) { this.next = next; return this; }

    void handle(Ticket ticket) {
        if (canHandle(ticket)) {
            resolve(ticket);
        } else if (next != null) {
            next.handle(ticket);
        } else {
            throw new IllegalStateException("No handler for ticket");
        }
    }

    abstract boolean canHandle(Ticket ticket);
    abstract void resolve(Ticket ticket);
}

SupportHandler chain = new TierOneSupport()
    .setNext(new TierTwoSupport()
    .setNext(new EngineeringEscalation()));
```

**When to use:** Middleware pipelines, event bubbling in UIs, support
ticket escalation, servlet filter chains — any "try each handler in turn."

**Trade-offs:** No single place in the code shows the whole chain's order —
you have to trace `setNext` calls to understand request flow.

---

### Command

**Intent:** Encapsulate a request as an object, allowing you to parameterize
clients with different requests, queue them, log them, and support undo.

**Problem:** You want to decouple the object that invokes an action (a
button, a menu item) from the object that knows how to perform it, and
possibly queue, log, or reverse that action later.

**Structure:** A `Command` interface declares `execute()` (and often
`undo()`); concrete commands capture everything needed to perform the
action, including a reference to the receiver.

**Example:**

```java
interface Command {
    void execute();
    void undo();
}

class AddTextCommand implements Command {
    private final Document doc;
    private final String text;
    AddTextCommand(Document doc, String text) { this.doc = doc; this.text = text; }

    public void execute() { doc.append(text); }
    public void undo() { doc.removeLast(text.length()); }
}

class CommandHistory {
    private final Deque<Command> history = new ArrayDeque<>();
    void run(Command cmd) { cmd.execute(); history.push(cmd); }
    void undoLast() { if (!history.isEmpty()) history.pop().undo(); }
}
```

**When to use:** Undo/redo stacks, task queues, GUI actions bound to
menu/toolbar/keyboard all invoking the same underlying command object.

**Trade-offs:** A class per action can proliferate quickly in a large
application; lambdas often replace simple Commands in modern code.

---

### Interpreter

**Intent:** Given a language, define a representation for its grammar
along with an interpreter that uses the representation to interpret
sentences in the language.

**Problem:** You need to evaluate expressions in a small domain-specific
language (search filters, pricing rules, regular expressions) repeatedly.

**Structure:** Each grammar rule becomes a class implementing a common
`Expression` interface with an `interpret(context)` method; complex
expressions are composed of simpler ones (itself a form of Composite).

**Example:**

```java
interface Expression {
    int interpret();
}

class Number implements Expression {
    int value;
    Number(int value) { this.value = value; }
    public int interpret() { return value; }
}

class Add implements Expression {
    Expression left, right;
    Add(Expression left, Expression right) { this.left = left; this.right = right; }
    public int interpret() { return left.interpret() + right.interpret(); }
}

// Represents "(3 + 4) + 5"
Expression expr = new Add(new Add(new Number(3), new Number(4)), new Number(5));
System.out.println(expr.interpret()); // 12
```

**When to use:** Small, stable, frequently-evaluated grammars — pricing
rule engines, simple query languages. For anything beyond toy complexity,
a real parser generator usually wins.

**Trade-offs:** Scales poorly to complex grammars — the class count grows
with grammar complexity, and performance of a naive tree-walking
interpreter can be a real bottleneck.

---

### Iterator

**Intent:** Provide a way to access the elements of an aggregate object
sequentially without exposing its underlying representation.

**Problem:** Client code needs to traverse a collection without knowing or
caring whether it's backed by an array, a linked list, or a tree.

**Structure:** An `Iterator` interface exposes `hasNext()`/`next()`; the
collection exposes an `iterator()` method returning one.

**Example:**

```java
class LinkedListNode<T> {
    T value;
    LinkedListNode<T> next;
}

class CustomIterator<T> implements Iterator<T> {
    private LinkedListNode<T> current;
    CustomIterator(LinkedListNode<T> head) { this.current = head; }

    public boolean hasNext() { return current != null; }
    public T next() {
        T value = current.value;
        current = current.next;
        return value;
    }
}
```

**When to use:** You're almost certainly already using this pattern every
time you write a Java `for (T item : collection)` loop — it's built into the
language via the `Iterable`/`Iterator` interfaces.

**Trade-offs:** Rarely a trade-off today; the pattern is so foundational
it's baked into most languages' syntax rather than hand-rolled.

---

### Mediator

**Intent:** Define an object that encapsulates how a set of objects
interact, promoting loose coupling by keeping objects from referring to
each other explicitly.

**Problem:** A set of objects need to communicate, but direct
many-to-many references between them create a tangled web that's hard to
change (every object knows about every other object).

**Structure:** A `Mediator` object sits between participants; each
participant talks only to the mediator, which coordinates the interaction.

**Example:**

```java
class ChatRoom { // the mediator
    void broadcast(User sender, String message) {
        for (User user : participants) {
            if (user != sender) user.receive(sender.name, message);
        }
    }
}

class User {
    String name;
    ChatRoom room;
    void send(String message) { room.broadcast(this, message); }
    void receive(String from, String message) { /* display it */ }
}
```

**When to use:** Chat rooms, air-traffic-control-style coordination, UI
widgets that must react to each other's state changes without each widget
knowing about every other widget directly.

**Trade-offs:** The mediator itself can become a god-object holding too
much coordination logic if it isn't kept disciplined.

---

### Memento

**Intent:** Without violating encapsulation, capture and externalize an
object's internal state so it can be restored to that state later.

**Problem:** You need undo/checkpoint functionality, but exposing an
object's full internal state to the outside world (so something else can
save and restore it) would break encapsulation.

**Structure:** The `Originator` creates a `Memento` snapshot of its own
state (so only it knows the memento's internal shape); a `Caretaker` stores
mementos opaquely, without inspecting their contents.

**Example:**

```java
class EditorState { // the memento - opaque to the caretaker
    private final String content;
    EditorState(String content) { this.content = content; }
    private String getContent() { return content; } // package-private access only
}

class Editor { // the originator
    private String content = "";
    void type(String text) { content += text; }
    EditorState save() { return new EditorState(content); }
    void restore(EditorState state) { this.content = state.getContent(); }
}

class History { // the caretaker - just stores snapshots, never reads them
    private final Deque<EditorState> snapshots = new ArrayDeque<>();
    void push(EditorState s) { snapshots.push(s); }
    EditorState pop() { return snapshots.pop(); }
}
```

**When to use:** Undo stacks in editors, transactional rollback, game save
states — anywhere you need point-in-time restoration without exposing
internals.

**Trade-offs:** Storing many full snapshots can be memory-expensive;
often needs an incremental/diff-based strategy at scale.

---

### Observer

**Intent:** Define a one-to-many dependency between objects so that when
one object changes state, all its dependents are notified automatically.

**Problem:** Multiple parts of a system need to react when something
changes, but the thing that changes shouldn't need to know the concrete
types of everything that cares about it.

**Structure:** A `Subject` maintains a list of `Observer`s and calls a
notification method on each whenever its state changes; observers
subscribe/unsubscribe dynamically.

**Example:**

```java
interface PriceObserver {
    void onPriceChanged(double newPrice);
}

class Stock {
    private double price;
    private final List<PriceObserver> observers = new ArrayList<>();

    void subscribe(PriceObserver o) { observers.add(o); }

    void setPrice(double price) {
        this.price = price;
        for (PriceObserver o : observers) o.onPriceChanged(price);
    }
}
```

**When to use:** Event systems, reactive UI frameworks, pub/sub messaging —
this is the conceptual ancestor of everything from DOM events to Spring's
`ApplicationEventPublisher`.

**Trade-offs:** Can create surprising update cascades that are hard to
trace (A notifies B, which triggers a change that notifies C...); memory
leaks if observers forget to unsubscribe.

---

### State

**Intent:** Allow an object to alter its behavior when its internal state
changes, appearing to change its class.

**Problem:** An object's behavior depends heavily on which state it's in,
and a sprawling if/else or switch on a state enum scattered across many
methods becomes unmanageable as states and transitions grow.

**Structure:** Each state is its own class implementing a common `State`
interface; the main object delegates behavior to its current state object
and swaps that reference on transitions.

**Example:**

```java
interface OrderState {
    OrderState next(Order order);
    String name();
}

class PendingState implements OrderState {
    public OrderState next(Order order) { return new ShippedState(); }
    public String name() { return "PENDING"; }
}

class ShippedState implements OrderState {
    public OrderState next(Order order) { return new DeliveredState(); }
    public String name() { return "SHIPPED"; }
}

class Order {
    private OrderState state = new PendingState();
    void advance() { state = state.next(this); }
}
```

**When to use:** Order/ticket/workflow state machines where behavior and
valid transitions genuinely differ per state.

**Trade-offs:** A class per state can be heavier than a simple enum +
switch for small state machines — reach for this once the per-state logic
is substantial, not for two or three trivial states.

---

### Strategy

**Intent:** Define a family of interchangeable algorithms, encapsulate each
one, and let the client pick which to use at runtime.

**Problem:** A class needs to support multiple variants of an algorithm
(different sorting orders, different pricing rules), and you don't want to
hard-code the choice or subclass for every variant.

**Structure:** A `Strategy` interface declares the algorithm's method; each
concrete strategy implements it; the client holds a reference to a
`Strategy` and delegates to it, swappable at runtime.

**Example:**

```java
interface DiscountStrategy {
    double apply(double price);
}

class NoDiscount implements DiscountStrategy {
    public double apply(double price) { return price; }
}

class PercentageDiscount implements DiscountStrategy {
    private final double percent;
    PercentageDiscount(double percent) { this.percent = percent; }
    public double apply(double price) { return price * (1 - percent / 100); }
}

class Checkout {
    private DiscountStrategy strategy = new NoDiscount();
    void setStrategy(DiscountStrategy s) { this.strategy = s; }
    double total(double price) { return strategy.apply(price); }
}
```

**When to use:** Interchangeable algorithms chosen at runtime — payment
methods, sorting comparators, pricing rules. In modern Java this is often a
lambda implementing a functional interface rather than a full class per
strategy.

**Trade-offs:** Easy to confuse with State (both swap behavior via an
interface reference) — the distinction is that Strategy is chosen by the
*client* for *how* to do something, while State is driven by the object's
*own* internal transitions.

---

### Template Method

**Intent:** Define the skeleton of an algorithm in a method, deferring some
steps to subclasses, so subclasses can redefine certain steps without
changing the algorithm's overall structure.

**Problem:** Several classes share the same overall algorithm but differ in
a few specific steps, and you want to avoid duplicating the shared
structure in every subclass.

**Structure:** An abstract base class defines a `final` template method
that calls a fixed sequence of steps, some concrete (shared) and some
abstract (overridden per subclass).

**Example:**

```java
abstract class DataExporter {
    final void export() { // template method - the algorithm's shape is fixed
        var data = fetchData();
        var formatted = format(data);
        writeToDestination(formatted);
    }

    abstract List<Row> fetchData();
    abstract String format(List<Row> data);

    void writeToDestination(String content) { // shared default
        System.out.println(content);
    }
}

class CsvExporter extends DataExporter {
    List<Row> fetchData() { return repository.findAll(); }
    String format(List<Row> data) { return toCsv(data); }
}
```

**When to use:** Multiple report generators, test setup/teardown skeletons
(JUnit's lifecycle methods are a version of this), data export pipelines
that share structure but differ in specific steps.

**Trade-offs:** Relies on inheritance, which is a tighter coupling than
composition-based alternatives like Strategy — prefer Strategy when the
varying piece is genuinely swappable at runtime rather than fixed per
subclass.

---

### Visitor

**Intent:** Represent an operation to be performed on the elements of an
object structure, letting you define a new operation without changing the
classes of the elements it operates on.

**Problem:** You have a stable hierarchy of element types (an AST's node
types, say) but need to keep adding new *operations* over that hierarchy
(pretty-printing, type-checking, code generation) without modifying every
element class each time.

**Structure:** Each element implements `accept(Visitor)`, which calls back
into a type-specific `visit(ThisType)` method on the visitor — a form of
double dispatch that routes to the right overload based on both the
element's and the visitor's type.

**Example:**

```java
interface ShapeVisitor {
    void visit(Circle c);
    void visit(Square s);
}

interface Shape {
    void accept(ShapeVisitor visitor);
}

class Circle implements Shape {
    double radius;
    public void accept(ShapeVisitor v) { v.visit(this); }
}

class Square implements Shape {
    double side;
    public void accept(ShapeVisitor v) { v.visit(this); }
}

class AreaCalculator implements ShapeVisitor {
    double totalArea = 0;
    public void visit(Circle c) { totalArea += Math.PI * c.radius * c.radius; }
    public void visit(Square s) { totalArea += s.side * s.side; }
}
```

**When to use:** Compilers/interpreters walking an AST, where element types
are stable but the set of operations (visitors) keeps growing.

**Trade-offs:** The inverse trade-off of Template Method — adding a new
*element type* requires touching every existing visitor, so this pattern
is a poor fit when element types change often but operations are stable.

---

## Choosing Between Similar Patterns

A few pairs are commonly confused:

- **Strategy vs. State** — both swap an interface implementation at
  runtime. Strategy is picked by the client, from the outside, to answer
  "how should this be done?" State is driven by the object itself, from the
  inside, as a reaction to its own transitions.
- **Decorator vs. Proxy** — both wrap an object behind the same interface.
  Decorator's purpose is to *add* behavior (and decorators compose — you
  can stack several). Proxy's purpose is to *control access* (lazy loading,
  permission checks) and typically wraps exactly one real object, not a
  chain.
- **Factory Method vs. Abstract Factory** — Factory Method is a single
  method, overridden to create one kind of product. Abstract Factory is a
  whole interface of creation methods, implemented to create a consistent
  *family* of related products together.
- **Adapter vs. Facade** — Adapter makes one existing interface match
  another interface you already depend on. Facade doesn't adapt an
  existing interface; it introduces a new, simpler interface on top of a
  complex subsystem that otherwise has no single entry point at all.
