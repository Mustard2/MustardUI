def status_progress(context, factor, text):
    """Show a progress bar in the middle of the status bar"""

    def draw(header, context):
        layout = header.layout
        layout.separator_spacer()
        row = layout.row()
        row.ui_units_x = 20
        row.progress(factor=factor, type="BAR", text=text)
        layout.separator_spacer()

    context.workspace.status_text_set(draw)
