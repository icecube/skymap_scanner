"""
    def stem_from_message_time(self):
        # provides uid based on timestamp
        # tentatively superseded
        sep = '-'
        buf = self.event['time']
        buf = buf.replace('-', '')
        buf = buf.replace(' ', sep)
        buf = buf.replace(':', '')
        buf = buf.replace('.', sep)
        return buf
"""
