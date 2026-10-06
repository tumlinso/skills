// Read-only CUDA Driver API inventory. No allocations, launches, peer enabling,
// clock changes or resets. Provided source was not compiled in the research session.
#include <cuda.h>
#include <iostream>
#include <string>
#include <vector>

static std::string quoted(const char* p) {
    std::string s="\"";
    if (p) for (const unsigned char c:std::string(p)) {
        if(c=='"'||c=='\\'){s+='\\';s+=char(c);}
        else if(c=='\n')s+="\\n";
        else if(c=='\r')s+="\\r";
        else if(c=='\t')s+="\\t";
        else if(c>=32)s+=char(c);
    }
    return s+'"';
}
static void error(CUresult r) {
    const char* n=nullptr;const char* d=nullptr;
    cuGetErrorName(r,&n);cuGetErrorString(r,&d);
    std::cout<<"{\"code\":"<<int(r)<<",\"name\":"<<quoted(n)
             <<",\"description\":"<<quoted(d)<<"}";
}
static void attribute(CUdevice dev,const char* name,CUdevice_attribute a,bool& comma) {
    int v=0;const CUresult r=cuDeviceGetAttribute(&v,a,dev);
    if(comma)std::cout<<',';comma=true;
    std::cout<<quoted(name)<<":{";
    if(r==CUDA_SUCCESS)std::cout<<"\"value\":"<<v<<",\"error\":null";
    else {std::cout<<"\"value\":null,\"error\":";error(r);}
    std::cout<<'}';
}
int main() {
    CUresult r=cuInit(0);
    if(r!=CUDA_SUCCESS){std::cout<<"{\"initialization_error\":";error(r);std::cout<<"}\n";return 1;}
    int n=0,driver=0;
    if((r=cuDeviceGetCount(&n))!=CUDA_SUCCESS){std::cout<<"{\"enumeration_error\":";error(r);std::cout<<"}\n";return 1;}
    cuDriverGetVersion(&driver);
    std::vector<CUdevice> devs;
    std::cout<<"{\"read_only\":true,\"driver_version\":"<<driver<<",\"devices\":[";
    for(int i=0;i<n;++i){
        CUdevice d; r=cuDeviceGet(&d,i);
        if(i)std::cout<<',';
        if(r!=CUDA_SUCCESS){std::cout<<"{\"ordinal\":"<<i<<",\"error\":";error(r);std::cout<<'}';continue;}
        devs.push_back(d);char name[256]={},bdf[64]={};
        cuDeviceGetName(name,sizeof(name),d);cuDeviceGetPCIBusId(bdf,sizeof(bdf),d);
        size_t bytes=0;CUresult mr=cuDeviceTotalMem(&bytes,d);
        std::cout<<"{\"ordinal\":"<<i<<",\"name\":"<<quoted(name)<<",\"pci_bus_id\":"<<quoted(bdf)<<",\"memory_bytes\":";
        if(mr==CUDA_SUCCESS)std::cout<<bytes;else std::cout<<"null";
        std::cout<<",\"memory_query_error\":";if(mr==CUDA_SUCCESS)std::cout<<"null";else error(mr);
        std::cout<<",\"attributes\":{";bool comma=false;
#define ATTR(label,ename) attribute(d,label,CU_DEVICE_ATTRIBUTE_##ename,comma)
        ATTR("cc_major",COMPUTE_CAPABILITY_MAJOR);ATTR("cc_minor",COMPUTE_CAPABILITY_MINOR);
        ATTR("sm_count",MULTIPROCESSOR_COUNT);ATTR("warp_size",WARP_SIZE);
        ATTR("max_threads_per_sm",MAX_THREADS_PER_MULTIPROCESSOR);
        ATTR("max_registers_per_sm",MAX_REGISTERS_PER_MULTIPROCESSOR);
        ATTR("max_shared_per_sm",MAX_SHARED_MEMORY_PER_MULTIPROCESSOR);
        ATTR("max_shared_per_block_optin",MAX_SHARED_MEMORY_PER_BLOCK_OPTIN);
        ATTR("async_engine_count",ASYNC_ENGINE_COUNT);ATTR("unified_addressing",UNIFIED_ADDRESSING);
        ATTR("managed_memory",MANAGED_MEMORY);ATTR("concurrent_managed_access",CONCURRENT_MANAGED_ACCESS);
        ATTR("pageable_memory_access",PAGEABLE_MEMORY_ACCESS);
        ATTR("host_page_tables",PAGEABLE_MEMORY_ACCESS_USES_HOST_PAGE_TABLES);
        ATTR("host_native_atomics",HOST_NATIVE_ATOMIC_SUPPORTED);
        ATTR("vmm",VIRTUAL_MEMORY_MANAGEMENT_SUPPORTED);ATTR("cooperative_launch",COOPERATIVE_LAUNCH);
        ATTR("cooperative_multi_device_launch",COOPERATIVE_MULTI_DEVICE_LAUNCH);
        ATTR("stream_64bit_memops",CAN_USE_64_BIT_STREAM_MEM_OPS);
        ATTR("stream_wait_nor",CAN_USE_STREAM_WAIT_VALUE_NOR);
        ATTR("remote_write_flush",CAN_FLUSH_REMOTE_WRITES);
#undef ATTR
        std::cout<<"}}";
    }
    std::cout<<"],\"ordered_pairs\":[";bool comma=false;
    for(size_t a=0;a<devs.size();++a)for(size_t b=0;b<devs.size();++b)if(a!=b){
        if(comma)std::cout<<',';comma=true;int access=0;
        r=cuDeviceCanAccessPeer(&access,devs[a],devs[b]);
        std::cout<<"{\"source_device_handle\":"<<devs[a]<<",\"destination_device_handle\":"<<devs[b]<<",\"can_access_peer\":";
        if(r==CUDA_SUCCESS)std::cout<<access;else std::cout<<"null";
        std::cout<<",\"access_error\":";if(r==CUDA_SUCCESS)std::cout<<"null";else error(r);
        const CUdevice_P2PAttribute attrs[]={CU_DEVICE_P2P_ATTRIBUTE_NATIVE_ATOMIC_SUPPORTED,CU_DEVICE_P2P_ATTRIBUTE_PERFORMANCE_RANK};
        const char* names[]={"native_atomic","performance_rank"};
        for(int j=0;j<2;++j){int v=0;r=cuDeviceGetP2PAttribute(&v,attrs[j],devs[a],devs[b]);
            std::cout<<','<<quoted(names[j])<<":{";
            if(r==CUDA_SUCCESS)std::cout<<"\"value\":"<<v<<",\"error\":null";
            else{std::cout<<"\"value\":null,\"error\":";error(r);}std::cout<<'}';}
        std::cout<<'}';
    }
    std::cout<<"]}\n";
    return 0;
}
