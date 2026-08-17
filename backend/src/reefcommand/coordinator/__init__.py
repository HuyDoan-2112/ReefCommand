"""The Coordinator: the only autonomous component in the pipeline.

Its purpose is not to pick whichever hypothesis has the largest score.
Its purpose is to determine what should happen next when the evidence is
incomplete or conflicting.

    thermal 0.91 / disease 0.17  ->  evidence is likely sufficient, proceed
    thermal 0.68 / disease 0.65  ->  ambiguous, and the two causes imply different
                                     actions, so request close-range lesion imagery

Everything upstream and downstream of this package is deterministic.
"""
