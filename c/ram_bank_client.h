/* Optional COLI_RAM_BANK client — peer RAM expert weight cache.
 * Gated by getenv("COLI_RAM_BANK"). When unset, all helpers are no-ops.
 * Protocol: GET <layer> <eid>\n → OK <wtot> <ftot>\n + weight + scales
 * See docs/pooled-ram.md. */
#ifndef COLI_RAM_BANK_CLIENT_H
#define COLI_RAM_BANK_CLIENT_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>

#ifndef _WIN32
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#endif

typedef struct {
    char host[256];
    int port;
} RamBankEp;

typedef struct {
    RamBankEp *eps;
    int n;
    int ready;
} RamBankPool;

static RamBankPool g_ram_bank;

static int ram_bank_route(int layer, int eid, int n){
    if(n<=0) return 0;
    return (int)(((unsigned)layer * 1315423911u + (unsigned)eid) % (unsigned)n);
}

static void ram_bank_init_once(void){
    if(g_ram_bank.ready) return;
    g_ram_bank.ready = 1;
    const char *raw = getenv("COLI_RAM_BANK");
    if(!raw || !raw[0]) return;
#ifdef _WIN32
    fprintf(stderr, "[RAM_BANK] COLI_RAM_BANK set but client is Linux/POSIX-only in this build\n");
    return;
#else
    char buf[4096];
    strncpy(buf, raw, sizeof(buf)-1);
    buf[sizeof(buf)-1] = 0;
    int cap = 8, n = 0;
    RamBankEp *eps = (RamBankEp*)malloc((size_t)cap * sizeof(RamBankEp));
    if(!eps) return;
    for(char *tok = strtok(buf, ","); tok; tok = strtok(NULL, ",")){
        while(*tok==' ') tok++;
        if(!*tok) continue;
        char *colon = strrchr(tok, ':');
        int port = 9400;
        if(colon && colon!=tok){
            *colon = 0;
            port = atoi(colon+1);
            if(port<=0) port = 9400;
        }
        if(n>=cap){
            cap *= 2;
            RamBankEp *nps = (RamBankEp*)realloc(eps, (size_t)cap * sizeof(RamBankEp));
            if(!nps){ free(eps); return; }
            eps = nps;
        }
        memset(&eps[n], 0, sizeof(eps[n]));
        strncpy(eps[n].host, tok, sizeof(eps[n].host)-1);
        eps[n].port = port;
        n++;
    }
    g_ram_bank.eps = eps;
    g_ram_bank.n = n;
    if(n>0) fprintf(stderr, "[RAM_BANK] %d peer(s) for expert weight cache\n", n);
#endif
}

/* Fill weight[0..wtot) and scales as float bytes ftot*4. Returns 1 on hit, 0 on miss/error. */
static int ram_bank_fetch(int layer, int eid, void *weight, int64_t wtot, void *scales, int64_t ftot){
    ram_bank_init_once();
#ifndef _WIN32
    if(g_ram_bank.n<=0 || !weight || !scales || wtot<=0 || ftot<0) return 0;
    int idx = ram_bank_route(layer, eid, g_ram_bank.n);
    RamBankEp *ep = &g_ram_bank.eps[idx];
    char portstr[16];
    snprintf(portstr, sizeof(portstr), "%d", ep->port);
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof(hints));
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_family = AF_UNSPEC;
    if(getaddrinfo(ep->host, portstr, &hints, &res)!=0 || !res) return 0;
    int fd = -1;
    for(struct addrinfo *ai=res; ai; ai=ai->ai_next){
        fd = (int)socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
        if(fd<0) continue;
        struct timeval tv; tv.tv_sec = 2; tv.tv_usec = 0;
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
        if(connect(fd, ai->ai_addr, ai->ai_addrlen)==0) break;
        close(fd); fd = -1;
    }
    freeaddrinfo(res);
    if(fd<0) return 0;
    char req[64];
    int n = snprintf(req, sizeof(req), "GET %d %d\n", layer, eid);
    if(n<=0 || write(fd, req, (size_t)n)!=n){ close(fd); return 0; }
    /* read status line */
    char line[128]; int lp=0;
    while(lp < (int)sizeof(line)-1){
        char c; ssize_t r = read(fd, &c, 1);
        if(r!=1){ close(fd); return 0; }
        if(c=='\n') break;
        line[lp++] = c;
    }
    line[lp]=0;
    if(strncmp(line, "OK ", 3)!=0){ close(fd); return 0; }
    long long got_w=0, got_f=0;
    if(sscanf(line+3, "%lld %lld", &got_w, &got_f)!=2){ close(fd); return 0; }
    if(got_w!=wtot || got_f!=ftot){ close(fd); return 0; }
    int64_t need_w = wtot, need_s = ftot*4;
    char *pw = (char*)weight;
    while(need_w>0){
        ssize_t r = read(fd, pw, (size_t)need_w);
        if(r<=0){ close(fd); return 0; }
        pw += r; need_w -= r;
    }
    char *ps = (char*)scales;
    while(need_s>0){
        ssize_t r = read(fd, ps, (size_t)need_s);
        if(r<=0){ close(fd); return 0; }
        ps += r; need_s -= r;
    }
    close(fd);
    return 1;
#else
    (void)layer; (void)eid; (void)weight; (void)wtot; (void)scales; (void)ftot;
    return 0;
#endif
}

#endif /* COLI_RAM_BANK_CLIENT_H */
