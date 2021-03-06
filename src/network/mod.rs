mod sender;
mod receiver;

use std::net::SocketAddr;
use std::sync::mpsc;
use std::sync::mpsc::Receiver;
use std::sync::mpsc::Sender;

use packet::Packet;
use LockedStream;


///
/// Starts a broadcast network using a subscription list.
///
/// The network recieves as input a sender and a receiver of two channels, respectively,
/// one for incoming packets and the other for outgoing packets.
///
/// Each machine maintains a list of subscriptions. The list defines
/// the IPs that this machine is listening to.
/// Initially, this list is provided as the parameter `init_remote_ips`
/// of the function `start_network`.
///
/// There are two modes for how connections are established:
///
/// * `is_two_way=false`: The list of IPs for subscription are
/// limited to those provided in `init_remote_ips` at the initialization.
/// The machine listens only to those IPs.
/// In this mode, it is possible that a one-way connection exists between some
/// machines, namely, a machine A listens to a machine B, but the machine B
/// does not listen to the machine A.
/// * `is_two_way=true`: The machine first subscribes and listens to all IPs provided
/// in `init_remote_ips` at the initialization.
/// In addition, the machine also subscribes to all other machines that are subscribing to
/// this machine, even if the IP of the other machine is not listed in `init_remote_ips`.
/// In this mode, two machine are either not listening to each other,
/// or connected in both directions (both listening to the other).
///
/// ## Parameters
/// * `init_remote_ips` - a list of IPs to which this computer makes a connection initially.
/// * `port` - the port number that the machines in the network are listening to.
/// `port` has to be the same value for all machines.
/// * `is_two_way` - a flag that indicates which IPs this machine will listen to.
/// See description above.
/// * `data_remote` - a sender of the channel for transmitting the data received from the network.
/// See the notes below.
/// * `data_local` - a reciever of the channel for transmitting the data to
/// be broadcasted to the network. See the notes below.
///
/// ## Notes
/// In order to send/receive data using the network, your program should first create
/// two [mpsc channels](https://doc.rust-lang.org/std/sync/mpsc/),
/// one for incoming packets, one for outgoing packets.
/// Then start the network using the `start_network` function,
/// and pass the sender or receiver of the two channels to the
/// network module as the function parameters.
/// The network module will broadcast out all packets received from the channel,
/// and also send the packets received from the network to the other channel.
/// Correspondingly, your program should write the data to be sent out to the channel,
/// and read the other channel to receive the packets from other machines.
/// See the example below for demonstration.
///
/// The network structure between the machines are decided by your program, specifically by
/// explicitly setting the list of IPs to be subscribed from each machine.
///
/// ## Design
///
/// Initially, the local computer only connects to the computers specificed by the
/// `init_remote_ips` vector in the function parameters (neighbors), and *receive* data from
/// these computers.
/// Specifically, a **Receiver** is created for each neighbor. The connection is initiated by the
/// Receiver. The number of Receivers on a computer is always equal to the number of neighbors.
/// On the other end, only one **Sender** is created for a computer, which send data to all other
/// computers that connected to it.
///
/// If `is_two_way` is set to `true`, for any remote computer B connected to the Sender on
/// the computer A, a new Receiver would also be created on A so that the connection between these
/// two computers are two-way.
/// If it is set to `false`, the Sender would only send local data to the remote computer (A -> B),
/// but it is possible that the remote computer might not send data to the local computer (B -> A),
/// since a corresponding receiver to the computer B might not exist on the computer A.
///
/// The full workflow of the network module is described in the following plot.
///
/// ![](https://www.lucidchart.com/publicSegments/view/9c3b7a65-55ad-4df5-a5cb-f3154b692ecd/image.png)
pub fn start_network(
        init_remote_ips: &Vec<String>, port: u16, is_two_way: bool,
        outbound_send: Sender<(Option<String>, Packet)>,
        outbound_recv: Receiver<(Option<String>, Packet)>,
        callback: Box<dyn FnMut(String, Packet) + Sync + Send>,
) -> Result<LockedStream, &'static str> {
    // receiver initiates the connection

    info!("Starting the network module.");
    let (ip_send, ip_recv): (Sender<SocketAddr>, Receiver<SocketAddr>) = mpsc::channel();
    // sender accepts remote connections
    let sender_state = {
        if is_two_way {
            sender::start_sender(port, outbound_recv, Some(ip_send.clone()))
        } else {
            sender::start_sender(port, outbound_recv, None)
        }
    };
    if sender_state.is_ok() {
        // receiver initiates remote connections
        receiver::start_receiver(port, outbound_send, callback, ip_recv);
        send_initial_ips(init_remote_ips, ip_send, port);
    }
    sender_state
}


#[allow(dead_code)]
fn start_network_only_send(
        port: u16, data_local: Receiver<(Option<String>, Packet)>,
) -> Result<LockedStream, &'static str> {
    info!("Starting the network (send only) module.");
    sender::start_sender(port, data_local, None)
}


#[allow(dead_code)]
fn start_network_only_recv(
    remote_ips: &Vec<String>, port: u16,
    outbound_send: Sender<(Option<String>, Packet)>,
    callback: Box<dyn FnMut(String, Packet) + Sync + Send>,
) -> Result<(), &'static str> {
    info!("Starting the network (receive only) module.");
    let (ip_send, ip_recv): (Sender<SocketAddr>, Receiver<SocketAddr>) = mpsc::channel();
    receiver::start_receiver(port, outbound_send, callback, ip_recv);
    send_initial_ips(remote_ips, ip_send, port);
    Ok(())
}


fn send_initial_ips(remote_ips: &Vec<String>, ip_send: Sender<SocketAddr>, port: u16) {
    remote_ips.iter().for_each(|ip| {
        let socket_addr: SocketAddr =
            (ip.clone() + ":" + port.to_string().as_str()).parse().expect(
                &format!("Failed to parse initial remote IP `{}:{}`.", ip, port)
            );
        ip_send.send(socket_addr).expect(
            "Failed to send the initial remote IP to the receivers listener."
        );
    });
}
