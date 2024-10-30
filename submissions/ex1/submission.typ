#import "../template/template.typ": template, code

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 1,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de"
)

== Exercise 2
In the Mango framework, Containers are kept separate from Agents to keep the network layer 
abstracted. 
Containers handle everything network-related, including sending and receiving messages 
between Agents. 
They take care of routing, serializing, and encoding messages based on the specific 
network communication technology in use.

Containers support multiple communication protocols, like TCP and MQTT, allowing Agents to 
focus solely on their business logic without needing to handle network details. 
This setup makes Agents easier to implement, more focused, and flexible across different 
network configurations.

#block(breakable: false)[
    Containers also optimize communication when possible. For example, the TCP container 
    checks if the target’s protocol address matches its own and avoids using the TCP 
    protocol if they’re the same. 
    This decision-making process, as shown in the following code snippet, boosts 
    performance automatically without requiring Agents to manage these optimizations:
    
    #code(
    filename: "mango/container/tcp.py", 
    start-line: 236,
    )[```python
    if protocol_addr == self.addr:
        # internal message
        meta["network_protocol"] = "tcp"
        success = self._send_internal_message(
            content, receiver_addr.aid, default_meta=meta
        )
    else:
        message = content
        # if the user does not provide a splittable content, we create the default one
        if not hasattr(content, "split_content_and_meta"):
            message = MangoMessage(content, meta)
        success = await self._send_external_message(
            receiver_addr.protocol_addr, message, meta
        )
    ```]
]

== Exercise 3

=== `Agent.__init__`
While Mango doesn’t explicitly define `__init__`, this constructor marks the start of an 
`Agent`'s lifecycle. 
In `__init__`, we can set initial values that make each agent unique, even if they share 
the same class. 
At this stage, Mango functions are not accessible, as the agent isn’t yet connected to a 
container.

=== `Agent.on_register`
At this lifecycle stage, the agent registers with a container, gaining an address, a 
context (which includes the container), and a scheduler. 
Now, it can schedule tasks, but message sending is still unavailable, as this only works 
when the container is fully running. 
We can, however, retrieve the agent’s address to enable messaging later.

=== `Agent.on_start`
In this stage, the container the agent lives in is fully running. 
Now, the agent can send and receive messages within this container, as its inbox task is 
active.
However, since other containers may still be initializing, sending messages should be 
handled with utmost care.

=== `Agent.on_ready`
At this point, all containers are operational, and every agent can fully send and receive 
messages. 
This is a good time to start inter-container communication with other agents.

=== `Agent.shutdown`
This hook is called during the container’s shutdown process, and it’s the time to handle 
any necessary cleanup. 
No further messages should be sent at this stage, as the system is wrapping up.

= Exercise 5
...

= Exercise 7
...

