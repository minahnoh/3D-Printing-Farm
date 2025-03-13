# environment_Customer.py
import simpy
import random
from config_SimPy import *


class Item:
    def __init__(self, id_order, id_patient, id_item):
        self.id_order = id_order
        self.id_patient = id_patient
        self.id_item = id_item
        self.type_item = "aligner"  # default
        self.is_completed = False
        self.is_defect = False  # Will be determined in Proc_Build


class Patient:
    def __init__(self, id_order, id_patient, items_creator_func):
        """
        Create a patient with the given IDs.

        Args:
            id_order: ID of the order this patient belongs to
            id_patient: ID of this patient
            items_creator_func: Function that creates items for this patient
        """
        self.id_order = id_order
        self.id_patient = id_patient
        self.num_items = NUM_ITEMS_PER_PATIENT()
        self.list_items = []
        self.is_completed = False

        # Create items for this patient using the provided function
        self.list_items = items_creator_func(
            id_order, id_patient, self.num_items)

    def check_completion(self):
        """Check if all items for this patient are completed"""
        if all(item.is_completed for item in self.list_items):
            self.is_completed = True
        return self.is_completed


class Order:
    def __init__(self, id_order, patients_creator_func):
        """
        Create an order with the given ID.

        Args:
            id_order: ID of this order
            patients_creator_func: Function that creates patients for this order
        """
        self.id_order = id_order
        self.num_patients = NUM_PATIENTS_PER_ORDER()
        self.list_patients = []
        self.due_date = ORDER_DUE_DATE
        self.time_start = None
        self.time_end = None

        # Create patients for this order using the provided function
        self.list_patients = patients_creator_func(id_order, self.num_patients)

    def check_completion(self):
        """Check if all patients in this order are completed"""
        if all(patient.check_completion() for patient in self.list_patients):
            return True
        return False


class OrderReceiver:
    """Interface for order receiving objects"""

    def receive_order(self, order):
        """Method to process orders (implemented by subclasses)"""
        pass


class SimpleOrderReceiver(OrderReceiver):
    """Simple order receiver for testing"""

    def __init__(self, env, logger=None):
        self.env = env
        self.logger = logger
        self.received_orders = []

    def receive_order(self, order):
        """Receive order and log it"""
        self.received_orders.append(order)
        self.logger.log_event(
            "Order", f"OrderReceiver recevied Order {order.id_order} (Patients: {order.num_patients}, Total items: {sum(len(patient.list_items) for patient in order.list_patients)})")


class Customer:
    def __init__(self, env, order_receiver, logger):
        self.env = env
        self.order_receiver = order_receiver
        self.logger = logger

        # Initialize ID counters
        self.order_counter = 1
        self.patient_counter = 1
        self.item_counter = 1

        # Automatically start the process when the Customer is created
        self.processing = env.process(self.create_order())

    def get_next_order_id(self):
        """Get next order ID and increment counter"""
        order_id = self.order_counter
        self.order_counter += 1
        return order_id

    def get_next_patient_id(self):
        """Get next patient ID and increment counter"""
        patient_id = self.patient_counter
        self.patient_counter += 1
        return patient_id

    def get_next_item_id(self):
        """Get next item ID and increment counter"""
        item_id = self.item_counter
        self.item_counter += 1
        return item_id

    def create_items_for_patient(self, id_order, id_patient, num_items):
        """Create items for a patient"""
        items = []
        for _ in range(num_items):
            item_id = self.get_next_item_id()
            items.append(Item(id_order, id_patient, item_id))
        return items

    def create_patients_for_order(self, id_order, num_patients):
        """Create patients for an order"""
        patients = []
        for _ in range(num_patients):
            patient_id = self.get_next_patient_id()
            patients.append(Patient(id_order, patient_id,
                            self.create_items_for_patient))
        return patients

    def create_new_order(self):
        """Create a new order"""
        order_id = self.get_next_order_id()
        return Order(order_id, self.create_patients_for_order)

    def create_order(self):
        """Create orders periodically"""
        while True:
            # Create a new order
            order = self.create_new_order()
            order.time_start = self.env.now

            # # Log order creation
            # self.logger.log_event(
            #     "Order", f"Created Order {order.id_order} (Patients: {order.num_patients}, Total items: {sum(len(patient.list_items) for patient in order.list_patients)})")

            # Send the order
            self.send_order(order)

            # Wait for next order cycle
            yield self.env.timeout(CUST_ORDER_CYCLE)

    def send_order(self, order):
        """Send the order to the receiver"""
        # if self.logger:
        #     self.logger.log_event(
        #         "Order", f"Sending Order {order.id_order} to processor")
        self.order_receiver.receive_order(order)


class SimpleLogger:
    """Class providing simple logging functionality"""

    def __init__(self, env):
        self.env = env

    def log_event(self, event_type, message):
        """Log events with timestamp"""
        current_time = self.env.now
        days = int(current_time // (24 * 60))
        hours = int((current_time % (24 * 60)) // 60)
        minutes = int(current_time % 60)
        timestamp = f"{days:02d}:{hours:02d}:{minutes:02d}"
        print(f"[{timestamp}] {event_type}: {message}")
