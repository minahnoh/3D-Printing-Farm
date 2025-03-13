# main_SimPy.py
import simpy
import time
import random
from config_SimPy import *
from environment_SimPy import Manager
from environment_Customer import Customer
from log_SimPy import Logger


def run_simulation(seed=None):
    """
    Run the manufacturing simulation

    Args:
        seed (int, optional): Random seed for reproducibility

    Returns:
        tuple: Manager and Logger instances
    """
    # Set random seed if provided
    if seed is not None:
        random.seed(seed)

    # Create simulation environment
    env = simpy.Environment()

    # Create manager
    manager = Manager(env)

    # Create logger
    logger = Logger(manager)

    # Create customer with manager as order receiver
    Customer(env, manager, logger)  # Auto-starts process in constructor

    # Start time measurement
    start_time = time.time()

    # Run simulation
    env.run(until=SIM_TIME)

    # End time measurement
    end_time = time.time()
    run_time = end_time - start_time
    print(f"\nSimulation completed in {run_time:.2f} seconds!")

    # Basic summary statistics
    print("========================================")
    print("\nSimulation Summary:")
    print(f"Total orders created: {len(manager.orders)}")
    print(f"Orders completed: {len(manager.completed_orders)}")
    print(f"Jobs processed: {len(manager.completed_jobs)}")
    print(f"Defective items identified: {len(manager.defective_items)}")

    # Collect statistics
    stats = logger.collect_statistics()

    # Display average makespan in days (always show this regardless of DETAILED_STATS_ENABLED)
    if 'order_makespan_avg' in stats:
        # Convert minutes to days
        avg_makespan_days = stats['order_makespan_avg'] / (24 * 60)
        print(f"\nAverage Order Makespan: {avg_makespan_days:.2f} days")
    else:
        print("\nNo completed orders to calculate average makespan.")

    # Display detailed statistics only if enabled
    if DETAILED_STATS_ENABLED:
        print("\nDetailed Statistics:")
        for key, value in sorted(stats.items()):
            if key.endswith('_std'):
                continue  # Skip standard deviations
            print(f"{key}: {value:.2f}")

    # Return the manager and logger for further analysis
    return manager, logger


def visualize_results(logger):
    """
    Visualize the simulation results using the logger

    Args:
        logger (Logger): The simulation logger
    """
    # Collect statistics
    stats = logger.collect_statistics()

    # Visualize all results - flags are checked within the method
    figures = logger.visualize_statistics(stats)

    # Return the figures for further customization if needed
    return figures


if __name__ == "__main__":
    # Set random seed for reproducibility
    RANDOM_SEED = 42

    # Run the simulation
    print(
        f"\nStarting simulation for {SIM_TIME} minutes ({SIM_TIME/60/24:.1f} days)...")
    manager, logger = run_simulation(seed=RANDOM_SEED)

    # Visualization status messages
    vis_enabled = VIS_STAT_ENABLED or GANTT_CHART_ENABLED

    if vis_enabled:
        print("\nGenerating visualizations...")

        # Show status for each type of visualization
        if GANTT_CHART_ENABLED:
            print("- Generating Gantt chart with job processing details")
        else:
            print("- Gantt chart visualization is disabled")

        if VIS_STAT_ENABLED:
            print("- Generating statistical graphs (queue lengths, utilization, etc.)")
        else:
            print("- Statistical visualization is disabled")

        figures = visualize_results(logger)
    else:
        print("\nAll visualizations are disabled. Adjust VIS_STAT_ENABLED and GANTT_CHART_ENABLED in config_SimPy.py to enable.")
