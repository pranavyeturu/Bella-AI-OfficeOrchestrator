def assign_ticket(ticket_id: str, user_id: str):
    """
    Call your helpdesk API to set `assignee = user_id`.
    """
    # e.g. requests.post(...); here we just log
    print(f"[TicketAPI] assign {ticket_id} → {user_id}")

def add_internal_note(ticket_id: str, note: str):
    """
    Add an internal comment to the ticket.
    """
    print(f"[TicketAPI] note on {ticket_id}: {note}")

def resolve_ticket(ticket_id: str):
    print(f"[TicketAPI] resolve {ticket_id}")
