# 3rd Party Host OS Configuration Modules for MOSK

Welcome to the collection of 3rd party-developed **Host OS Configuration Modules** for **Mirantis OpenStack for Kubernetes (MOSK)**. This repository contains various configuration modules created and contributed by Mirantis Professional Services, Customer Support teams, partners, and users of Mirantis' products.

## ⚠️ Disclaimer

- **Mirantis does not guarantee** that any of the contributed modules will be functional at any time or will be compatible with the latest version of MOSK.
- **Mirantis is not responsible** for any damage, issues, or disruptions caused by the usage of these modules, use these modules **at your own risk** and test them in a safe environment before deploying them in production.

## 📌 What is This Repository For?

This repository serves as a community-driven collection of host OS configuration modules, which can be used to fine-tune the underlying host operating system for MOSK deployments. Contributors from the community, Mirantis professional services, and customer support teams can publish their modules here.

## 🚀 Getting Started

To use any of the modules from this repository:

1. Clone the repository:
   ```sh
   git clone https://github.com/your-org/mosk-host-os-modules.git
   cd mosk-host-os-modules
   ```
2. Browse the available modules in the respective directories.
3. Follow the provided documentation or instructions within each module's folder to build it.
4. Publish the built binary to a HTTP server where your MOSK management cluster can reach it.
5. Following the instructions provided in [MOSK Operations Guide :: Bare metal operations :: Host OS configuration](https://docs.mirantis.com/mosk/latest/ops/bm-operations/host-os-conf.html) for adding a custom module. This is achieved by creating a new HostOSConfigurationModules custom resource in the MOSK management cluster API.
6. Create a new HostOSConfiguration referring to the new module by name, passing necessary parameters and targeting the nodes by labels.

## 📜 Contribution Guidelines

We encourage contributions from the Mirantis community! If you have developed a module that you believe would benefit others, feel free to contribute it by following these steps:

1. **Fork** this repository.
2. **Create a new branch** for your module:
   ```sh
   git checkout -b feature-new-module
   ```
3. **Add your module** to the appropriate directory, along with a README file explaining how it works.
4. **Submit a Pull Request (PR)** with a clear description of your module.

### Contribution Requirements
- Ensure your module is well-documented.
- Include a `README.md` explaining the purpose and usage of the module.
- Do not include proprietary or sensitive information.

## 🛠 Support & Issues

Since this is a **community-driven** repository, there is **no official support from Mirantis**. However, if you encounter an issue or have a question, you can:

- Open an **Issue** on this repository.
- Engage with the community for discussions and solutions.

## 📄 License

This repository is open-source and distributed under the **Apache 2.0 License**. See the [LICENSE](LICENSE) file for more details.

---

We appreciate your contributions and efforts in making MOSK a more flexible and configurable platform! 🚀
