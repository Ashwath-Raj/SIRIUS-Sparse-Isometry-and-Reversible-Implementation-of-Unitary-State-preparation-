import unittest
from scripts.hardware_probe import parse_nvidia_smi_csv, memory_info

class HardwareProbeTests(unittest.TestCase):
    def test_parse_nvidia_smi_csv(self):
        data='NVIDIA GeForce RTX 3050 Laptop GPU, GPU-abc, 6144 MiB, 550.54.14\n'
        got=parse_nvidia_smi_csv(data)
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]['name'],'NVIDIA GeForce RTX 3050 Laptop GPU')
        self.assertEqual(got[0]['memory_total'],'6144 MiB')
    def test_empty_nvidia_output(self):
        self.assertEqual(parse_nvidia_smi_csv(''),[])
    def test_memory_info_shape(self):
        got=memory_info()
        self.assertIn('total_bytes',got)
        if got['total_bytes'] is not None: self.assertGreater(got['total_bytes'],0)

if __name__=='__main__': unittest.main()
