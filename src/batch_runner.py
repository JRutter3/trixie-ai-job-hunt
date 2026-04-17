"""Class for executing the main batch of the program."""
# I get an ick if there is any logic in the main besides parsing command line args.

class TrixieJob:
    """Class that represents a single "TrixieJob" instance."""
    def __init__(self):
        """Initializes a TrixieJob"""
        ...

    def run_job(self):
        """Executes the TrixieJob."""
        # Step 1: Fetch appropriate e-mails from the inbox
        # Step 2: Send them off to the AI agent for categorization.
        # Step 3: Notify of results
        #   NOTE: Step 3 will likely evolve to "store results" and the notification will
        #   run as a separate batch for summaries etc.
        ...
