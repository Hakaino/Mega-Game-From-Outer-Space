import shelve
import pygame
pygame.init()
progress = shelve.open("progress.dat")

progress["level"] = 1
progress["block"] = 64 #number of bits in a square block side
progress["sizeX"] = 1280 #must try to find how to get the best screen resolution
progress["sizeY"] = 800
progress["FPS"] = 50
progress["music"] = False
progress["multiplayer"] = True
progress["P1_keyboard"] = True
progress["P2_keyboard"] = True

progress["P1_keys"] = [
    pygame.K_a,
    2,
    pygame.K_SPACE,
    pygame.K_g,
    pygame.K_p,
    pygame.K_r,
    pygame.K_t,
     8,
    pygame.K_ESCAPE,
    10, 11,
    pygame.K_d,
    pygame.K_a,
    pygame.K_w,
    pygame.K_s]

progress["P2_keys"] = [
    pygame.K_a,
    2,
    pygame.K_SPACE,
    pygame.K_g,
    pygame.K_p,
    pygame.K_r,
    pygame.K_t,
     8,
    pygame.K_z,#ESCAPE,
    10, 11,
    pygame.K_RIGHT,
    pygame.K_LEFT,
    pygame.K_UP,
    pygame.K_DOWN]

progress.close()
print ("Progress Saved!")
