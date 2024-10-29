#import "./template/template.typ": template, code

#show: template.with(
  course: "Agent-based Control in Energy Systems", 
  authors: ("Tim Hesse", "Michael Krah").sorted(),
  group: 8,
  number: 1,
  tutor: "Rico Schrage",
  tutor-mail: "rico.schrage@uni-oldenburg.de"
)

= Exercise 2
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

= Exercise 3
...

= Exercise 5
...

= Exercise 7
...

