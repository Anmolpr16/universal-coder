from universal_coder.models import Message, ModelResponse, ModelCapabilities, StreamChunk
class MockProvider:
    name='mock'
    capabilities=ModelCapabilities(tool_calling=True,streaming=True,structured_output=True)
    def generate(self,messages,tools):
        return ModelResponse(Message('assistant','Mock provider: runtime is operational. Connect a real model to perform coding tasks.'))
    def stream(self,messages,tools):
        text='Mock provider: runtime is operational. Connect a real model to perform coding tasks.'
        for word in text.split(' '): yield StreamChunk(word+' ')
        yield StreamChunk(done=True)
