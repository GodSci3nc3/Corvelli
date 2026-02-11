/**
 * Configuration Templates
 * Common network configurations for quick deployment
 */

export const templates = {
  basic_vlan: {
    name: "VLAN Básica",
    description: "Crear VLAN con nombre",
    icon: "network",
    vendors: ["cisco", "juniper", "arista", "hp"],
    params: [
      { name: "vlan_id", type: "number", label: "VLAN ID", required: true },
      { name: "name", type: "string", label: "Nombre", required: true }
    ],
    promptTemplate: (params) => {
      return `Crea la VLAN ${params.vlan_id} con nombre ${params.name}`;
    },
    generate: (vendor, params) => {
      if (vendor === 'cisco' || vendor === 'arista') {
        return `vlan ${params.vlan_id}\nname ${params.name}`;
      }
      if (vendor === 'juniper') {
        return `set vlans ${params.name} vlan-id ${params.vlan_id}`;
      }
      if (vendor === 'hp') {
        return `vlan ${params.vlan_id}\nname ${params.name}`;
      }
      return `vlan ${params.vlan_id}\nname ${params.name}`;
    }
  },

  trunk_port: {
    name: "Puerto Trunk",
    description: "Configurar trunk entre switches",
    icon: "link",
    vendors: ["cisco", "juniper", "arista", "hp"],
    params: [
      { name: "interface", type: "string", label: "Interfaz", required: true },
      { name: "allowed_vlans", type: "string", label: "VLANs permitidas", required: false, default: "all" }
    ],
    promptTemplate: (params) => {
      const vlans = params.allowed_vlans || "all";
      return `Configura la interfaz ${params.interface} como trunk permitiendo VLANs ${vlans}`;
    },
    generate: (vendor, params) => {
      const vlans = params.allowed_vlans || "all";
      
      if (vendor === 'cisco' || vendor === 'arista') {
        return `interface ${params.interface}\nswitchport mode trunk\nswitchport trunk allowed vlan ${vlans}`;
      }
      if (vendor === 'juniper') {
        return `set interfaces ${params.interface} unit 0 family ethernet-switching interface-mode trunk\nset interfaces ${params.interface} unit 0 family ethernet-switching vlan members ${vlans}`;
      }
      if (vendor === 'hp') {
        return `interface ${params.interface}\ntagged vlan ${vlans}`;
      }
      return `interface ${params.interface}\nswitchport mode trunk\nswitchport trunk allowed vlan ${vlans}`;
    }
  },

  access_port: {
    name: "Puerto de Acceso",
    description: "Conectar PC o servidor a VLAN",
    icon: "port",
    vendors: ["cisco", "juniper", "arista", "hp"],
    params: [
      { name: "interface", type: "string", label: "Interfaz", required: true },
      { name: "vlan_id", type: "number", label: "VLAN ID", required: true },
      { name: "description", type: "string", label: "Descripción", required: false }
    ],
    promptTemplate: (params) => {
      let prompt = `Configura la interfaz ${params.interface} como access en la VLAN ${params.vlan_id}`;
      if (params.description) {
        prompt += ` con descripción "${params.description}"`;
      }
      return prompt;
    },
    generate: (vendor, params) => {
      const desc = params.description ? `\ndescription ${params.description}` : '';
      
      if (vendor === 'cisco' || vendor === 'arista') {
        return `interface ${params.interface}${desc}\nswitchport mode access\nswitchport access vlan ${params.vlan_id}\nno shutdown`;
      }
      if (vendor === 'juniper') {
        return `set interfaces ${params.interface} unit 0 family ethernet-switching interface-mode access\nset interfaces ${params.interface} unit 0 family ethernet-switching vlan members ${params.vlan_id}`;
      }
      if (vendor === 'hp') {
        return `interface ${params.interface}${desc}\nuntagged vlan ${params.vlan_id}`;
      }
      return `interface ${params.interface}${desc}\nswitchport mode access\nswitchport access vlan ${params.vlan_id}\nno shutdown`;
    }
  },

  port_security: {
    name: "Port Security",
    description: "Seguridad básica en puerto",
    icon: "lock",
    vendors: ["cisco", "hp"],
    params: [
      { name: "interface", type: "string", label: "Interfaz", required: true },
      { name: "max_macs", type: "number", label: "MACs máximas", required: false, default: 1 }
    ],
    promptTemplate: (params) => {
      const max = params.max_macs || 1;
      return `Configura port security en ${params.interface} con máximo ${max} MAC${max > 1 ? 's' : ''}`;
    },
    generate: (vendor, params) => {
      const max = params.max_macs || 1;
      
      if (vendor === 'cisco') {
        return `interface ${params.interface}\nswitchport port-security\nswitchport port-security maximum ${max}\nswitchport port-security violation restrict\nswitchport port-security mac-address sticky`;
      }
      if (vendor === 'hp') {
        return `interface ${params.interface}\nport-security max-mac-count ${max}\nport-security address-limit ${max}`;
      }
      return `interface ${params.interface}\nswitchport port-security\nswitchport port-security maximum ${max}`;
    }
  },

  default_gateway: {
    name: "Default Gateway / SVI",
    description: "IP en VLAN para routing",
    icon: "gateway",
    vendors: ["cisco", "juniper", "arista"],
    params: [
      { name: "vlan_id", type: "number", label: "VLAN ID", required: true },
      { name: "ip", type: "string", label: "IP Address", required: true },
      { name: "mask", type: "string", label: "Subnet Mask", required: false, default: "255.255.255.0" }
    ],
    promptTemplate: (params) => {
      const mask = params.mask || "255.255.255.0";
      return `Configura IP ${params.ip} ${mask} en la VLAN ${params.vlan_id}`;
    },
    generate: (vendor, params) => {
      const mask = params.mask || "255.255.255.0";
      
      if (vendor === 'cisco' || vendor === 'arista') {
        return `interface vlan ${params.vlan_id}\nip address ${params.ip} ${mask}\nno shutdown`;
      }
      if (vendor === 'juniper') {
        const cidr = maskToCIDR(mask);
        return `set interfaces vlan unit ${params.vlan_id} family inet address ${params.ip}/${cidr}`;
      }
      return `interface vlan ${params.vlan_id}\nip address ${params.ip} ${mask}\nno shutdown`;
    }
  },

  ospf_single_area: {
    name: "OSPF Single Area",
    description: "OSPF básico en área 0",
    icon: "broadcast",
    vendors: ["cisco", "juniper"],
    params: [
      { name: "process_id", type: "number", label: "Process ID", required: false, default: 1 },
      { name: "network", type: "string", label: "Network", required: true },
      { name: "wildcard", type: "string", label: "Wildcard", required: false, default: "0.0.0.255" },
      { name: "area", type: "number", label: "Area", required: false, default: 0 }
    ],
    promptTemplate: (params) => {
      const process = params.process_id || 1;
      const wildcard = params.wildcard || "0.0.0.255";
      const area = params.area || 0;
      return `Configura OSPF proceso ${process} para la red ${params.network} ${wildcard} en el área ${area}`;
    },
    generate: (vendor, params) => {
      const process = params.process_id || 1;
      const wildcard = params.wildcard || "0.0.0.255";
      const area = params.area || 0;
      
      if (vendor === 'cisco') {
        return `router ospf ${process}\nnetwork ${params.network} ${wildcard} area ${area}`;
      }
      if (vendor === 'juniper') {
        return `set protocols ospf area 0.0.0.${area} interface lo0.0`;
      }
      return `router ospf ${process}\nnetwork ${params.network} ${wildcard} area ${area}`;
    }
  }
};

// Helper function: Convert subnet mask to CIDR
function maskToCIDR(mask) {
  const parts = mask.split('.');
  let cidr = 0;
  for (let part of parts) {
    const num = parseInt(part);
    cidr += (num.toString(2).match(/1/g) || []).length;
  }
  return cidr;
}

export function getAvailableTemplates(vendor = 'cisco') {
  return Object.entries(templates)
    .filter(([id, template]) => template.vendors.includes(vendor))
    .map(([id, template]) => ({
      id,
      name: template.name,
      description: template.description,
      icon: template.icon,
      params: template.params
    }));
}

export function applyTemplate(templateId, vendor, params) {
  const template = templates[templateId];
  if (!template) {
    throw new Error('Template not found');
  }
  
  if (!template.vendors.includes(vendor)) {
    throw new Error(`Template not compatible with ${vendor}`);
  }
  
  // Validate required params
  for (const param of template.params) {
    if (param.required && !params[param.name]) {
      throw new Error(`Missing required parameter: ${param.name}`);
    }
  }
  
  // Fill defaults
  const filledParams = { ...params };
  for (const param of template.params) {
    if (param.default && !filledParams[param.name]) {
      filledParams[param.name] = param.default;
    }
  }
  
  return {
    prompt: template.promptTemplate(filledParams),
    commands: template.generate(vendor, filledParams)
  };
}
